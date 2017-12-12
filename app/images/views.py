import sys

from ..schemata import tune
from io import BytesIO
from . import images
import numpy as np
from ..schemata import experiment, shared, reso, meso, stack, pupil, treadmill, tune
from flask import render_template, redirect, url_for, flash, request, session, send_from_directory, make_response
import matplotlib.pyplot as plt
import mpld3
import seaborn as sns
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.colors as mcolors
import matplotlib.image as mpimg

size_factor = dict(
    thumb=2, small=4, medium=8, large=16, huge=32
)
corr_cmap = sns.blend_palette(['dodgerblue', 'steelblue', 'k', 'lime', 'orange'], as_cmap=True)


def savefig(fig, **kwargs):
    canvas = FigureCanvas(fig)
    png_output = BytesIO()
    canvas.print_png(png_output, dpi=50, **kwargs)
    response = make_response(png_output.getvalue())
    response.headers['Content-Type'] = 'image/png'
    plt.close(fig)
    return response


@images.route("/oracle-<int:animal_id>-<int:session>-<int:scan_idx>-<int:field>_<size>.png")
def oracle_map(animal_id, session, scan_idx, field, size):
    key = dict(animal_id=animal_id, session=session, scan_idx=scan_idx, field=field)
    print('Oracle', key)

    img = (tune.OracleMap() & key).fetch1('oracle_map')

    sz = tuple(i / max(*img.shape) * size_factor[size] for i in reversed(img.shape))

    fig, ax = plt.subplots(figsize=sz)

    ax.imshow(img, origin='lower', interpolation='nearest', cmap=corr_cmap, vmin=-1, vmax=1)
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return savefig(fig)


@images.route("/correlation-<int:animal_id>-<int:session>-<int:scan_idx>-<int:field>_<size>.png")
def correlation_image(animal_id, session, scan_idx, field, size):
    key = dict(animal_id=animal_id, session=session, scan_idx=scan_idx, field=field)
    base = meso if meso.ScanInfo() & key else reso

    img = (base.SummaryImages.Correlation() & key).fetch1('correlation_image')

    sz = tuple(i / max(*img.shape) * size_factor[size] for i in reversed(img.shape))
    fig, ax = plt.subplots(figsize=sz)

    ax.imshow(img, origin='lower', interpolation='nearest', cmap=corr_cmap, vmin=-1, vmax=1)
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return savefig(fig)


@images.route("/average-<int:animal_id>-<int:session>-<int:scan_idx>-<int:field>_<size>.png")
def average_image(animal_id, session, scan_idx, field, size):
    key = dict(animal_id=animal_id, session=session, scan_idx=scan_idx, field=field)
    base = meso if meso.ScanInfo() & key else reso
    img = (base.SummaryImages.Average() & key).fetch1('average_image')

    sz = tuple(i / max(*img.shape) * size_factor[size] for i in reversed(img.shape))
    fig, ax = plt.subplots(figsize=sz)

    ax.imshow(img, origin='lower', interpolation='nearest', cmap='gray')
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return savefig(fig)


@images.route("/contrast_intensity-<int:animal_id>-<int:session>-<int:scan_idx>-<int:field>_<size>.png")
def contrast_intensity(animal_id, session, scan_idx, field, size):
    key = dict(animal_id=animal_id, session=session, scan_idx=scan_idx, field=field)
    base = meso if meso.ScanInfo() & key else reso
    inten, contr = (base.Quality.MeanIntensity() * base.Quality.Contrast() & key).fetch1('intensities',
                                                                                         'contrasts')

    sz = tuple(i * size_factor[size] for i in [.9, .5])
    with  sns.plotting_context('talk' if size == 'huge' else 'paper'):
        with sns.axes_style('ticks'):
            fig, (ax, ax2) = plt.subplots(2, 1, figsize=sz, sharex=True)
            ax.plot(inten, label='mean intensity', color='dodgerblue', lw=1)
            ax.set_ylabel('intensity')
            ax2.set_ylabel('contrast')
            ax2.plot(contr, label='contrast', color='deeppink', lw=1)
            ax2.set_xlabel('frame number')
            fig.tight_layout()
            fig.subplots_adjust(left=.2)
            sns.despine(fig, trim=True)
            for a in [ax, ax2]:
                a.spines['bottom'].set_linewidth(1)
                a.spines['left'].set_linewidth(1)
                a.tick_params(axis='both', length=3)
    return savefig(fig)


@images.route("/cos2map-<int:animal_id>-<int:session>-<int:scan_idx>-<int:field>_<size>.png")
def cos2map(animal_id, session, scan_idx, field, size):
    key = dict(animal_id=animal_id, session=session, scan_idx=scan_idx, field=field)

    a, m = (tune.Cos2Map() & key).fetch1('direction_map', 'amplitude_map')
    h = (a / np.pi / 2) % 1
    v = np.minimum(m / np.percentile(m, 99.9), 1)

    img = mcolors.hsv_to_rgb(np.stack((h, v, v), axis=2))
    sz = tuple(i / max(*img.shape) * size_factor[size] for i in reversed(img.shape[:2]))
    fig, ax = plt.subplots(figsize=sz)
    ax.imshow(img, origin='lower', interpolation='nearest') 
    ax.axis('off')
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    return savefig(fig)


@images.route("/eye-<int:animal_id>-<int:session>-<int:scan_idx>_<size>.png")
def eye(animal_id, session, scan_idx, size):
    key = dict(animal_id=animal_id, session=session, scan_idx=scan_idx)

    frames = (pupil.Eye() & key).fetch1('preview_frames')

    sz = tuple(i * size_factor[size] for i in [1,9/16])
    with sns.axes_style('white'):
        fig, ax = plt.subplots(4, 4, figsize=sz, sharex=True, sharey=True)
        vmin, vmax = frames.min(), frames.max()
        for fr, a in zip(frames.transpose([2,0,1]), ax.ravel()):
            a.imshow(fr, vmin=vmin, vmax=vmax, cmap='gray')
            a.axis('off')
        fig.set_facecolor('k')
        fig.subplots_adjust(wspace=0, hspace=0, left=0, right=1, bottom=0, top=1)
    return savefig(fig)
