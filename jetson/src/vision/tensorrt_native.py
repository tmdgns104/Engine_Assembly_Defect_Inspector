"""Worker-owned TensorRT 10 executor. Native libraries load only at activation."""
import ctypes as ct
import hashlib
import json
import math
import time
import numpy as np

from src.contracts import DetectorError
from src.contracts.interfaces import FatalDetectorError
from src.vision.cuda_runtime_ctypes import CudaRuntime


class NativeTensorRTExecutor:
    """Persistent I/O and one stream/context. No fallback, retry or global reset."""
    def __init__(self, package, *, trt_module=None, cuda=None, device_index=0,
                 max_buffer_bytes=256 * 1024 * 1024):
        self.state = 'INITIALIZING'
        self.closed = False
        self.in_flight = False
        self.unsafe_completion = False
        self.context = self.engine = self.runtime = self.logger = None
        self.stream = None
        self.cuda = cuda
        self.buffers = {}
        self.execute_count = 0
        self.last_timing = None
        self.close_errors = []
        self.device_index = device_index
        manifest = package.manifest
        contract = manifest['detector']
        if not contract['input'].get('name'):
            raise FatalDetectorError('TENSORRT_NATIVE_CONTRACT_NON_EXECUTABLE')
        if manifest['files']['model']['artifact_format'] != 'trt_plan':
            raise FatalDetectorError('ARTIFACT_FORMAT_UNSUPPORTED')
        try:
            plan = package.model_path.read_bytes()
        except OSError as error:
            raise FatalDetectorError('ENGINE_MISSING: '+str(error)) from error
        self.engine_sha = hashlib.sha256(plan).hexdigest()
        if self.engine_sha != manifest['files']['model']['sha256']:
            raise FatalDetectorError('ARTIFACT_HASH_MISMATCH')
        self.input_contract = dict(contract['input'])
        self.output_contract = dict(contract['output']['tensor_shape_contract'])
        self.input_name = self.input_contract['name']
        self.output_name = self.output_contract['name']
        stage = 'NATIVE_RUNTIME_LOAD_FAILED'
        try:
            if trt_module is None:
                import tensorrt as trt_module
            self.trt = trt_module
            if self.cuda is None:
                self.cuda = CudaRuntime()
            self.cuda.set_device(device_index)
            self.logger = self.trt.Logger(self.trt.Logger.WARNING)
            self.runtime = self.trt.Runtime(self.logger)
            stage = 'ENGINE_DESERIALIZE_FAILED'
            self.engine = self.runtime.deserialize_cuda_engine(plan)
            if self.engine is None:
                raise RuntimeError('deserialize returned None')
            stage = 'BINDING_CONTRACT_MISMATCH'
            self.io = self._validate_io(max_buffer_bytes)
            stage = 'CONTEXT_CREATE_FAILED'
            self.context = self.engine.create_execution_context()
            if self.context is None:
                raise RuntimeError('context returned None')
            stage = 'CUDA_STREAM_CREATE_FAILED'
            self.stream = self.cuda.create_stream()
            stage = 'CUDA_ALLOCATION_FAILED'
            for description in self.io:
                name, size = description['name'], description['bytes']
                owned = self.buffers[name] = {'host': None, 'device': None, 'array': None}
                owned['host'] = self.cuda.allocate_host(size)
                byte_view = (ct.c_ubyte * size).from_address(owned['host'])
                owned['array'] = np.ctypeslib.as_array(byte_view).view(
                    np.dtype(description['dtype'])).reshape(description['shape'])
                owned['device'] = self.cuda.allocate_device(size)
            stage = 'BINDING_CONTRACT_MISMATCH'
            for name, owned in self.buffers.items():
                if not self.context.set_tensor_address(name, owned['device']):
                    raise RuntimeError('set_tensor_address returned False: '+name)
            self.state = 'READY'
        except Exception as error:
            primary = FatalDetectorError(stage+': '+str(error))
            try:
                self.close()
            except Exception as cleanup:
                primary.cleanup_errors = [str(cleanup)]
                if hasattr(primary, 'add_note'):
                    primary.add_note(str(cleanup))
            raise primary from error

    def _validate_io(self, limit):
        if type(limit) is not int or limit <= 0:
            raise ValueError('Invalid resource limit')
        expected = {self.input_name: (self.input_contract, self.trt.TensorIOMode.INPUT),
                    self.output_name: (self.output_contract, self.trt.TensorIOMode.OUTPUT)}
        names = [self.engine.get_tensor_name(i) for i in range(self.engine.num_io_tensors)]
        if len(expected) != 2 or len(names) != 2 or set(names) != set(expected):
            raise ValueError('I/O names/count')
        result = []
        for name in names:
            declared, mode = expected[name]
            if not isinstance(name, str) or not name.strip() or '\0' in name or len(name.encode()) >= 4096:
                raise ValueError('tensor name')
            shape = tuple(self.engine.get_tensor_shape(name))
            dtype = np.dtype(self.trt.nptype(self.engine.get_tensor_dtype(name)))
            if (shape != tuple(declared['shape']) or dtype.name != declared['dtype']
                    or dtype.name not in ('float16', 'float32')
                    or self.engine.get_tensor_mode(name) != mode):
                raise ValueError('tensor shape/dtype/mode: '+name)
            if any(type(value) is not int or value <= 0 for value in shape):
                raise ValueError('dynamic/invalid dimensions')
            if (self.engine.get_tensor_location(name) != self.trt.TensorLocation.DEVICE
                    or self.engine.get_tensor_format(name) != self.trt.TensorFormat.LINEAR
                    or self.engine.get_tensor_vectorized_dim(name) != -1
                    # TRT10.3 reports -1 (not 1) when the tensor is not vectorized.
                    or self.engine.get_tensor_components_per_element(name) != -1
                    or self.engine.is_shape_inference_io(name)):
                raise ValueError('unsupported location/format/vectorization/shape I/O: '+name)
            size = math.prod(shape) * dtype.itemsize
            if not 0 < size <= min(limit, ct.c_size_t(-1).value, np.iinfo(np.intp).max):
                raise ValueError('unsafe buffer size')
            result.append({'name': name, 'shape': list(shape), 'dtype': dtype.name,
                           'mode': 'INPUT' if mode == self.trt.TensorIOMode.INPUT else 'OUTPUT',
                           'location': 'DEVICE', 'format': 'LINEAR', 'vectorized_dim': -1,
                           'bytes': size})
        return result

    def _synchronize(self):
        try:
            self.cuda.synchronize(self.stream)
        except Exception:
            self.unsafe_completion = True
            raise
        self.in_flight = False

    def execute(self, input_array):
        if self.closed or self.state != 'READY':
            raise FatalDetectorError('INFERENCE_FAILED: native executor unavailable')
        if (not isinstance(input_array, np.ndarray)
                or input_array.shape != tuple(self.input_contract['shape'])
                or input_array.dtype.name != self.input_contract['dtype']
                or not input_array.flags.c_contiguous or not np.isfinite(input_array).all()):
            raise DetectorError('INPUT_CONTRACT_MISMATCH: native input')
        source = self.buffers[self.input_name]
        output = self.buffers[self.output_name]
        start = time.perf_counter()
        stage = 'CUDA_COPY_FAILED: H2D'
        try:
            np.copyto(source['array'], input_array, casting='no')
            h2d_start = time.perf_counter()
            self.in_flight = True
            self.cuda.copy_async(source['device'], source['host'], source['array'].nbytes, 1, self.stream)
            h2d_end = time.perf_counter()
            stage = 'INFERENCE_FAILED'
            enqueue_start = time.perf_counter()
            if not self.context.execute_async_v3(stream_handle=self.stream):
                raise RuntimeError('execute_async_v3 returned False')
            stage = 'CUDA_SYNCHRONIZE_FAILED'
            self._synchronize()
            complete = time.perf_counter()
            stage = 'CUDA_COPY_FAILED: D2H'
            self.in_flight = True
            self.cuda.copy_async(output['host'], output['device'], output['array'].nbytes, 2, self.stream)
            stage = 'CUDA_SYNCHRONIZE_FAILED'
            self._synchronize()
            copied = time.perf_counter()
            result = output['array'].copy()
            self.execute_count += 1
            self.last_timing = {
                'native_host_total_ms': (time.perf_counter()-start)*1000,
                'h2d_enqueue_host_ms': (h2d_end-h2d_start)*1000,
                'enqueue_through_completion_ms': (complete-enqueue_start)*1000,
                'd2h_through_completion_ms': (copied-complete)*1000,
                'scope': 'host observed; enqueue-through-completion includes queued H2D; not pure GPU kernel time'}
            return {self.output_name: result}
        except Exception as error:
            self.state = 'INVALIDATED'
            raise FatalDetectorError(stage+': '+str(error)) from error

    def runtime_metadata(self):
        return json.loads(json.dumps({
            'backend': 'tensorrt', 'tensorrt_version': self.trt.__version__,
            'cuda_runtime_version': None, 'device_index': self.device_index,
            'engine_sha256': self.engine_sha, 'io': self.io,
            'stream_mode': 'nondefault_nonblocking', 'state': self.state,
            'execute_count': self.execute_count, 'cuda_call_counts': self.cuda.call_counts,
            'last_timing': self.last_timing, 'close_errors': self.close_errors}, allow_nan=False))

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.in_flight and not self.unsafe_completion:
            try:
                self._synchronize()
            except Exception as error:
                self.close_errors.append(str(error))
        if self.unsafe_completion:
            self.state = 'CLOSE_FAILED'
            self.close_errors.append('completion unknown; resources retained for process exit')
            raise FatalDetectorError('DETECTOR_CLOSE_FAILED: '+ '; '.join(self.close_errors))
        self.context = None
        for owned in self.buffers.values():
            owned['array'] = None
            for key, release in [('device', self.cuda.free_device), ('host', self.cuda.free_host)]:
                pointer = owned[key]
                owned[key] = None  # Never retry an uncertain free result.
                if pointer is not None:
                    try:
                        release(pointer)
                    except Exception as error:
                        self.close_errors.append(str(error))
        if self.stream is not None:
            stream, self.stream = self.stream, None
            try:
                self.cuda.destroy_stream(stream)
            except Exception as error:
                self.close_errors.append(str(error))
        self.engine = self.runtime = self.logger = None
        self.state = 'CLOSE_FAILED' if self.close_errors else 'CLOSED'
        if self.close_errors:
            raise FatalDetectorError('DETECTOR_CLOSE_FAILED: '+ '; '.join(self.close_errors))
