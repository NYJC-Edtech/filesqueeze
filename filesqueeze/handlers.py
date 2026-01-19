from .fsm import Format, Handler, State
from .fsm.enums import Video, Slideshow
from . import video, pptx


def cleanupFiles(state: State) -> None:
    """
    Final transition of state machine.
    Removes origin file.
    """
    # state.origin.unlink()
    state.status_complete()
    return None

def analyzeVideo(state: State) -> Handler:
    """
    Analyses a video file, fills in metadata, and returns an appropriate handler.
    """
    state.status_analyze()
    try:
        duration = video.duration(str(state.target))
        size = video.width_height(str(state.target))
    except Exception:
        state.status = "Error during file analysis"
        # No need to terminate; can still proceed without metadata
    else:
        if duration:
            state.metadata['duration'] = duration
        if size:
            state.metadata['width'], state.metadata['height'] = size
    finally:
        return compressVideo

def analyzeSlideshow(state: State) -> Handler:
    """
    TODO: Detect PPTX files that contain a single video.
    For now, does nothing and returns a converter handler.
    """
    state.status_analyze()
    state.set_target(state.origin)
    return pptxToVideo

def pptxToVideo(state: State) -> Handler:
    """
    Converts a pptx file into a video file.
    """
    state.status_convert()
    outfile = (state.target.parent / (state.target.stem + '.mp4')).as_posix()
    try:
        pptx.to_mp4(str(state.target), outfile)
    except Exception:
        state.error("Error converting PPTX file")
        # TODO: clean up outfile
    else:
        state.set_target(outfile)
        return selectAnalyzer
    return cleanupFiles

def compressVideo(state: State) -> Handler:
    """
    Compresses a video file.
    """
    state.status_compress()
    outfile = state.target.parent.joinpath('compressed_' + state.target.name)  # TODO: generate temp folder
    # import pdb; pdb.set_trace()
    try:
        video.compress(
            str(state.target),
            str(outfile),
            downscale=(True if state.metadata.get('height', 0) > 720 else False),
        )
    except Exception:
        # TODO: clean up outfile
        state.error("Error compressing MP4 video")
    else:
        state.set_target(outfile)
    finally:
        return cleanupFiles

def selectAnalyzer(
    state: State,
    handler={
        Video: analyzeVideo,
        Slideshow: analyzeSlideshow,
    },
) -> Handler:
    """
    First transition of state machine.
    Detects origin format and returns an appropriate handler for analysis.
    """
    # Map format enums to their handlers
    suffix = state.target.suffix.lstrip('.').upper()  # Enums store file extension in uppercase
    for format in Format:
        format = format.value  # format is an Enum within the Format enum
        if suffix in format.__members__:
            state.set_format(format[suffix])  # get Enum member using suffix
            return handler[type(format[suffix])]

    # No matching target format found
    state.error("File type cannot be handled")
    return cleanupFiles
