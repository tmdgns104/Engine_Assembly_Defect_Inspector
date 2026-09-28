"""Fixed-bench background comparison, independent of the engine detector.

No reference learning, camera access, image resizing or file writes occur here.
The reference bank contains only reviewed empty images. A whole-image reference
is chosen; pixels from different references are never spliced together.
"""
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter


class UnavailableOccupancy:
    """A missing/invalid background must not take ownership of camera health."""
    def __init__(self, version, reason):
        self.version, self.reason = version, reason

    def evaluate(self, image):
        return dict(config_version=self.version,reference_version='UNAVAILABLE',
                    reference_valid=False,classification='UNKNOWN',reason=self.reason,
                    regions={},comparison_ms=0.)


def load_area_occupancy(path):
    path=Path(path)
    version='MISSING_AREA_CONFIG'
    try:
        raw=path.read_bytes()
        version=hashlib.sha256(raw).hexdigest()
        if json.loads(raw).get('mode')=='DARK_SURFACE_SELF_OBSERVED':
            return DarkSurfaceOccupancy.from_config(path,raw)
        return BackgroundOccupancy.from_config(path)
    except (OSError,ValueError,KeyError,TypeError) as error:
        return UnavailableOccupancy(version,'AREA_REFERENCE_UNAVAILABLE:'+type(error).__name__)


class DarkSurfaceOccupancy:
    """Bench-only object check on the dark work surface in each native frame.

    The surface edges are located again in every frame. No empty image is
    retained, compared, learned or approved. An unrecognized surface is UNKNOWN.
    """
    def __init__(self, config, config_version):
        self.config=config
        self.config_version=config_version

    @classmethod
    def from_config(cls,path,raw=None):
        raw=Path(path).read_bytes() if raw is None else raw
        config=json.loads(raw)
        if (config.get('mode')!='DARK_SURFACE_SELF_OBSERVED' or
                config.get('roi')!='DYNAMIC_DARK_SURFACE_FULL_HEIGHT' or
                config.get('color')!='BGR_UINT8' or config.get('shape')!=[720,1280,3] or
                config.get('references')):
            raise ValueError('UNSUPPORTED_DARK_SURFACE_CONFIG')
        for key, expected in dict(clear_seconds=1.2,clear_minimum_frames=6,
                                  maximum_gap_seconds=.5,maximum_age_seconds=1.).items():
            if config.get(key)!=expected:
                raise ValueError('UNSUPPORTED_AREA_CONTINUITY_POLICY:'+key)
        return cls(config,hashlib.sha256(raw).hexdigest())

    def evaluate(self,image):
        import cv2
        import numpy as np
        started=perf_counter()
        result=dict(config_version=self.config_version,
                    reference_version='DARK_SURFACE_GEOMETRY_V1',
                    reference_valid=False,classification='UNKNOWN',regions={})
        if (image is None or image.dtype!=np.uint8 or
                list(image.shape)!=self.config['shape']):
            return dict(result,reason='IMAGE_GEOMETRY_OR_FORMAT_INVALID')
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        # Locate the current dark surface from many rows, not from one stored
        # empty view. Side borders and the camera mount are outside this surface.
        edges=[]
        for y in range(120,640,8):
            xs=np.flatnonzero(gray[y]<125)
            if len(xs)>600:
                edges.append((int(xs[0]),int(xs[-1])))
        if len(edges)<40:
            return dict(result,reason='DARK_SURFACE_GEOMETRY_UNKNOWN')
        left=int(np.median([edge[0] for edge in edges]))
        right=int(np.median([edge[1] for edge in edges]))
        width=right-left
        height,image_width=gray.shape
        geometry=dict(left=left,right=right,valid_rows=len(edges),width=width)
        result['regions']={'surface_geometry':geometry}
        if not (.12*image_width<=left<=.22*image_width and
                .74*image_width<=right<=.89*image_width and
                .58*image_width<=width<=.72*image_width):
            return dict(result,reason='DARK_SURFACE_GEOMETRY_UNKNOWN')
        # A small side-border allowance prevents the white workbench edge from
        # becoming a permanent object. The complete bottom exit stays observed.
        inner_left,inner_right=left+18,right-12
        interior=gray[120:640,inner_left:inner_right]
        dark_fraction=float(np.count_nonzero(interior<125)/interior.size)
        geometry['dark_fraction']=dark_fraction
        if dark_fraction<.55:
            return dict(result,reason='DARK_SURFACE_NOT_RECOGNIZED')
        hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
        # The mat's illuminated texture can reach moderate saturation. The
        # retained gold handle has a much stronger color signal at the exit.
        foreground=np.logical_or(gray>135,
            np.logical_and(hsv[:,:,1]>100,hsv[:,:,2]>90)).astype(np.uint8)
        foreground[:,:inner_left]=0
        foreground[:,inner_right:]=0
        # A tiny camera translation can reveal a uniform bright strip above
        # the work surface. It is a frame border, not a localized object. A
        # wider strip invalidates geometry instead of being ignored.
        top_border=0
        for y in range(6):
            if np.count_nonzero(foreground[y,inner_left:inner_right])<.8*(inner_right-inner_left):
                break
            top_border+=1
        if top_border>5:
            return dict(result,reason='DARK_SURFACE_TOP_BORDER_CHANGED')
        foreground[:top_border,:]=0
        # The camera mount can leave a few horizontal pixels at the top edge
        # when the view shifts. Ignore only a wide, <=5 px tall edge sliver;
        # a local object extending farther into the work surface still blocks.
        count,labels,stats,_=cv2.connectedComponentsWithStats(foreground,8)
        for index in range(1,count):
            _,component_y,component_width,component_height,_=stats[index]
            if (component_y==0 and component_height<=5 and
                    component_width>=50 and component_width>=10*component_height):
                foreground[labels==index]=0

        def largest(mask,y_offset=0):
            count,_,stats,_=cv2.connectedComponentsWithStats(mask,8)
            if count<=1:return 0,None
            index=int(stats[1:,4].argmax())+1
            box=stats[index,:4].tolist()
            box[1]+=y_offset
            return int(stats[index,4]),box

        whole,whole_box=largest(foreground)
        bottom,bottom_box=largest(foreground[-64:],height-64)
        result['regions'].update(largest_component_pixels=whole,
            largest_component_box=whole_box,bottom_component_pixels=bottom,
            bottom_component_box=bottom_box,foreground_pixels=int(foreground.sum()))
        result['comparison_ms']=(perf_counter()-started)*1000
        result['reference_valid']=True
        if whole>=80 or bottom>=30:
            return dict(result,classification='OCCUPIED',reason='DARK_SURFACE_OBJECT_PRESENT')
        return dict(result,classification='MATCH',reason='DARK_SURFACE_NO_OBJECT')


class BackgroundOccupancy:
    def __init__(self, config, references, config_version):
        import cv2
        import numpy as np
        self.config = config
        self.config_version = config_version
        self.references = [(name, image.astype(np.int16)) for name, image in references]
        # Fixed local illumination compensation preserves native-resolution edges.
        # No erosion/opening is used: it could remove the remaining thin handle.
        size = config['illumination_kernel_pixels']
        self.details = [(name, cv2.subtract(image, cv2.blur(image, (size, size))))
                        for name, image in self.references]
        # A small object at an exit can be subtracted by the 41 px local mean.
        # Keep the whole-image test and add a wider illumination scale at the
        # two bench exits. This does not mask any pixels or lower thresholds.
        exit_size = config['exit_illumination_kernel_pixels']
        self.exit_details = [cv2.subtract(image, cv2.blur(image, (exit_size, exit_size)))
                             for _, image in self.references]

    @classmethod
    def from_config(cls, path):
        import cv2
        path = Path(path)
        raw = path.read_bytes()
        config = json.loads(raw)
        if config['roi'] != 'FULL_NATIVE_IMAGE_NO_MASK' or config['color'] != 'BGR_UINT8':
            raise ValueError('UNSUPPORTED_AREA_REFERENCE_GEOMETRY')
        # These bounds are shared with Runtime/evidence validation, not tunable
        # through a reference approval. A policy change needs code and regression.
        for key, expected in dict(clear_seconds=1.2,clear_minimum_frames=6,
                                  maximum_gap_seconds=.5,maximum_age_seconds=1.).items():
            if config[key] != expected: raise ValueError('UNSUPPORTED_AREA_CONTINUITY_POLICY:'+key)
        references = []
        for item in config['references']:
            source = path.parent / item['path']
            if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('AREA_REFERENCE_HASH_MISMATCH')
            image = cv2.imread(str(source))
            if image is None or list(image.shape) != config['shape']:
                raise ValueError('AREA_REFERENCE_DIMENSIONS_MISMATCH')
            references.append((item['id'], image))
        if not references:
            raise ValueError('AREA_REFERENCE_REQUIRED')
        return cls(config, references, hashlib.sha256(raw).hexdigest())

    def evaluate(self, image):
        import cv2
        import numpy as np
        started = perf_counter()
        result = dict(config_version=self.config_version,
                      reference_version=self.config['reference_version'],
                      reference_valid=True, classification='UNKNOWN', regions={})
        if (image is None or image.dtype != np.uint8 or
                list(image.shape) != self.config['shape']):
            return dict(result, reference_valid=False, reason='IMAGE_GEOMETRY_OR_FORMAT_INVALID')
        value = image.astype(np.int16)
        size = self.config['illumination_kernel_pixels']
        detail = cv2.subtract(value, cv2.blur(value, (size, size)))
        exit_size = self.config['exit_illumination_kernel_pixels']
        exit_detail = cv2.subtract(value, cv2.blur(value, (exit_size, exit_size)))
        candidates = []
        for (name, reference), (_, reference_detail), exit_reference in zip(
                self.references, self.details, self.exit_details):
            raw_difference = np.abs(value[::8, ::8] - reference[::8, ::8])
            raw_mean = float(raw_difference.mean())
            blue, green, red = cv2.split(cv2.absdiff(detail, reference_detail))
            delta = cv2.max(cv2.max(blue, green), red)
            mask = cv2.compare(delta, self.config['pixel_difference'], cv2.CMP_GT)
            count, labels, stats, centers = cv2.connectedComponentsWithStats(mask, 8)
            largest = int(stats[1:, 4].max()) if count > 1 else 0
            index = int(stats[1:, 4].argmax()) + 1 if count > 1 else None
            regions = dict(whole_fraction=cv2.countNonZero(mask)/mask.size, largest_component_pixels=largest,
                largest_component_box=stats[index, :4].tolist() if index else None,
                right_edge_changed_pixels=cv2.countNonZero(mask[:, -64:]),
                bottom_edge_changed_pixels=cv2.countNonZero(mask[-64:, :]),
                left_edge_changed_pixels=cv2.countNonZero(mask[:, :64]),
                top_edge_changed_pixels=cv2.countNonZero(mask[:64, :]), raw_mean_difference=raw_mean)
            exits = self._exit_residuals(exit_detail, exit_reference, value, reference)
            regions['exit_residuals'] = exits
            exit_largest = max(region['component_pixels'] for region in exits.values())
            regions['exit_largest_component_pixels'] = exit_largest
            # Select one coherent reference for both tests; never splice the
            # most favourable reference separately for each region or scale.
            candidates.append((max(largest, exit_largest), regions['whole_fraction'], name, regions))
        _, _, selected, regions = min(candidates)
        result.update(reference_selected=selected, regions=regions,
                      comparison_ms=(perf_counter()-started)*1000)
        if regions['raw_mean_difference'] > self.config['max_raw_mean_difference']:
            return dict(result, reason='LARGE_ILLUMINATION_OR_BACKGROUND_CHANGE')
        if (regions['largest_component_pixels'] >= self.config['occupied_component_pixels'] or
                regions['whole_fraction'] >= self.config['occupied_fraction']):
            return dict(result, classification='OCCUPIED', reason='LOCAL_BACKGROUND_DIFFERENCE')
        if regions['exit_largest_component_pixels'] >= self.config['occupied_component_pixels']:
            return dict(result, classification='OCCUPIED', reason='EXIT_BACKGROUND_RESIDUAL')
        return dict(result, classification='MATCH', reason='REVIEWED_EMPTY_BACKGROUND_MATCH')

    def _exit_residuals(self, detail, reference, image, background):
        """Measure native-resolution residuals in right/bottom exit bands."""
        import cv2
        band = self.config['exit_band_pixels']
        height, width = detail.shape[:2]
        regions = {}
        for name, y, x in [('right', 0, width-band), ('bottom', height-band, 0)]:
            current = detail[y:, x:]
            baseline = reference[y:, x:]
            blue, green, red = cv2.split(cv2.absdiff(current, baseline))
            delta = cv2.max(cv2.max(blue, green), red)
            mask = cv2.compare(delta, self.config['pixel_difference'], cv2.CMP_GT)
            # Local-mean subtraction can create a halo on an unchanged dark
            # bench edge when the adjacent table becomes brighter. Require
            # support in the original pixels too; never count a filter halo
            # alone as a remaining object. Both thresholds remain unchanged.
            blue, green, red = cv2.split(cv2.absdiff(image[y:, x:], background[y:, x:]))
            native_delta = cv2.max(cv2.max(blue, green), red)
            native_support = cv2.compare(native_delta, self.config['pixel_difference'], cv2.CMP_GT)
            mask = cv2.bitwise_and(mask, native_support)
            count, labels, stats, centers = cv2.connectedComponentsWithStats(mask, 8)
            index = int(stats[1:, 4].argmax()) + 1 if count > 1 else None
            box = stats[index, :4].tolist() if index else None
            if box:
                box[0] += x
                box[1] += y
            regions[name] = dict(component_pixels=int(stats[index, 4]) if index else 0,
                                 component_box=box, changed_pixels=cv2.countNonZero(mask))
        return regions


class ClearWindow:
    """Continuity is source-time based; missing/replayed input never advances it."""
    def __init__(self, duration=1.2, minimum_frames=6, maximum_gap=.5, maximum_age=1.):
        self.duration = duration
        self.minimum_frames = minimum_frames
        self.maximum_gap = maximum_gap
        self.maximum_age = maximum_age
        self.previous = None
        self.samples = []

    def reset(self):
        self.previous = None
        self.samples = []

    def update(self, measurement, metadata, now):
        keys = ('frame_id','sequence','camera_epoch','monotonic_s','generation')
        result = dict(measurement, **{key:metadata[key] for key in keys},
                      source_timestamp=metadata.get('source_timestamp',metadata.get('freshness',{}).get('source_pts_ns')),
                      state='UNKNOWN', clear_duration_s=0., clear_sequences=[])
        current = dict(metadata, config_version=measurement['config_version'],
                       reference_version=measurement['reference_version'])
        previous = self.previous
        self.previous = current
        source = metadata['monotonic_s']
        invalid = None
        if not math.isfinite(source) or not 0 <= now-source <= self.maximum_age or not metadata['integrity']['valid']:
            invalid = 'INVALID_OR_STALE_AREA_FRAME'
        elif not measurement['reference_valid']:
            invalid = 'AREA_REFERENCE_INVALID'
        elif previous is not None:
            if any(current[k] != previous[k] for k in ('camera_epoch','generation','config_version','reference_version')):
                invalid = 'AREA_REFERENCE_OR_EPOCH_CHANGED'
            elif (metadata['frame_id'] == previous['frame_id'] or
                    metadata['sequence'] <= previous['sequence'] or source <= previous['monotonic_s']):
                invalid = 'AREA_FRAME_ORDER_INVALID'
            elif (metadata['sequence'] != previous['sequence']+1 or
                  source-previous['monotonic_s'] > self.maximum_gap):
                invalid = 'AREA_FRAME_GAP'
        if invalid:
            self.samples = []
            return dict(result, reason=invalid)
        if measurement['classification'] != 'MATCH':
            self.samples = []
            return dict(result, state=measurement['classification'])
        self.samples.append((metadata['sequence'], source))
        # Keep sufficient history without an unbounded per-frame allocation.
        while len(self.samples) > self.minimum_frames and source-self.samples[1][1] >= self.duration:
            self.samples.pop(0)
        span = source-self.samples[0][1]
        clear = len(self.samples) >= self.minimum_frames and span+1e-9 >= self.duration
        return dict(result, state='CLEAR' if clear else 'UNKNOWN',
                    reason='AREA_CLEAR_CONFIRMED' if clear else 'CLEAR_DURATION_PENDING',
                    clear_duration_s=span, clear_sequences=[s for s,t in self.samples],
                    first_clear_monotonic=self.samples[0][1])
