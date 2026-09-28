"""Small checked CUDA Runtime ABI boundary; importing this module loads no CUDA."""
import ctypes as ct

LIBCUDART = '/usr/local/cuda-12.6/targets/aarch64-linux/lib/libcudart.so.12.6.68'


class CudaRuntimeError(RuntimeError):
    def __init__(self, operation, status, name, detail):
        self.operation, self.status = operation, status
        super().__init__(f'{operation}: status={status} {name}: {detail}')


class CudaRuntime:
    """Explicit ownership is held by the caller, not by hidden object destructors."""
    def __init__(self, *, library=None, observer=None):
        self.library = ct.CDLL(LIBCUDART) if library is None else library
        self.observer = observer
        self.call_counts = {}
        pointer = ct.c_void_p
        handle_out = ct.POINTER(pointer)
        signatures = {
            'cudaSetDevice': [ct.c_int],
            'cudaMalloc': [handle_out, ct.c_size_t],
            'cudaMallocHost': [handle_out, ct.c_size_t],
            'cudaFree': [pointer], 'cudaFreeHost': [pointer],
            'cudaStreamCreateWithFlags': [handle_out, ct.c_uint],
            'cudaStreamSynchronize': [pointer], 'cudaStreamDestroy': [pointer],
            'cudaMemcpyAsync': [pointer, pointer, ct.c_size_t, ct.c_int, pointer],
        }
        for name, args in signatures.items():
            function = getattr(self.library, name)
            function.argtypes, function.restype = args, ct.c_int
        for name in ('cudaGetErrorName', 'cudaGetErrorString'):
            function = getattr(self.library, name)
            function.argtypes, function.restype = [ct.c_int], ct.c_char_p

    def _call(self, name, *args):
        status = int(getattr(self.library, name)(*args))
        self.call_counts[name] = self.call_counts.get(name, 0) + 1
        if self.observer is not None:
            self.observer({'operation': name, 'status': status})
        if status:
            error_name = self.library.cudaGetErrorName(status) or b'UNKNOWN'
            error_text = self.library.cudaGetErrorString(status) or b'UNKNOWN'
            raise CudaRuntimeError(name, status, error_name.decode('utf-8', 'replace'),
                                   error_text.decode('utf-8', 'replace'))

    @staticmethod
    def _size(size):
        if type(size) is not int or not 0 < size <= ct.c_size_t(-1).value:
            raise ValueError('Invalid CUDA byte count')

    def set_device(self, index):
        if type(index) is not int or index < 0:
            raise ValueError('Invalid CUDA device index')
        self._call('cudaSetDevice', index)

    def _allocate(self, operation, size):
        self._size(size)
        pointer = ct.c_void_p()
        self._call(operation, ct.byref(pointer), size)
        if pointer.value is None:
            raise RuntimeError(operation + ': success with null pointer')
        return pointer.value

    def allocate_device(self, size):
        return self._allocate('cudaMalloc', size)

    def allocate_host(self, size):
        return self._allocate('cudaMallocHost', size)

    def free_device(self, pointer):
        self._call('cudaFree', ct.c_void_p(pointer))

    def free_host(self, pointer):
        self._call('cudaFreeHost', ct.c_void_p(pointer))

    def create_stream(self):
        stream = ct.c_void_p()
        self._call('cudaStreamCreateWithFlags', ct.byref(stream), 1)
        if stream.value is None:
            raise RuntimeError('cudaStreamCreateWithFlags: null stream')
        return stream.value

    def synchronize(self, stream):
        self._call('cudaStreamSynchronize', ct.c_void_p(stream))

    def destroy_stream(self, stream):
        self._call('cudaStreamDestroy', ct.c_void_p(stream))

    def copy_async(self, destination, source, size, kind, stream):
        self._size(size)
        if kind not in (1, 2):
            raise ValueError('Only explicit H2D or D2H copies are supported')
        self._call('cudaMemcpyAsync', ct.c_void_p(destination), ct.c_void_p(source),
                   size, kind, ct.c_void_p(stream))
