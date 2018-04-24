import argparse
import logging
import os
from timeit import default_timer as timer

import matplotlib
matplotlib.use('Agg') # Fixes weird segfaults, see http://matplotlib.org/faq/howto_faq.html#matplotlib-in-a-web-application-server

from fsm_load_modal_composites import load_modal_composites
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d import Axes3D
import numpy as np


__version__ = '1.0.0'


FIGURE_SIZE = (11.7, 8.3) # In inches

DEFAULT_A = 1000.0

SUBPLOTS_SPEC = [
    {
        'x': 'sigma_cr',
        'y': 'omega',
    },
    {
        'x': 'm_dominant',
        'y': 'omega',
    },
    {
        'x': 'm_dominant',
        'y': 'sigma_cr',
    },
    {
        'x': 'sigma_cr',
        'y': 'omega',
        'z': 'm_dominant',
    },
]


def plot_modal_composite(modal_composites, column_units, column_descriptions):
    logging.info("Plotting modal composites...")
    start = timer()

    def _get_column_title(column_name):
        description = column_descriptions[column_name].split(',')[0]
        unit = column_units[column_name]
        return description if not unit else "%s [%s]" % (description, unit)

    a = modal_composites['a'][0]
    t_b = modal_composites['t_b']
    plt.suptitle("strip length %.4f [mm], strip thickness %.4f - %.4f [mm]" % (a, np.min(t_b), np.max(t_b)))

    for ax_idx, spec in enumerate(SUBPLOTS_SPEC, start=1):
        ax = plt.subplot(2, 2, ax_idx, projection='3d' if 'z' in spec else 'rectilinear')

        data = [modal_composites[data_key] for _, data_key in sorted(spec.items())]
        ax.scatter(*data, s=2)

        for ax_key, data_key in spec.items():
            set_label = getattr(ax, "set_%slabel" % ax_key)
            set_label(_get_column_title(data_key))

    logging.info("Plotting completed in %f second(s)", timer() - start)

def dynamic_load_modal_composites(model_file, search_buffer=10**-10, **filters):
    modal_composites, column_units, column_descriptions = load_modal_composites(model_file, **filters)

    if modal_composites.size != 0:
        return modal_composites, column_units, column_descriptions

    a = filters.pop('a_fix')
    filters.update({
        'a_min': a - search_buffer,
        'a_max': a + search_buffer,
    })

    logging.warn("Could not find the exact value of a requested, expanding search condition to %(a_min)s <= a <= %(a_max)s", filters)
    return load_modal_composites(model_file, **filters)


def analyze_model(model_file, report_file, **filters):
    with PdfPages(report_file) as pdf:
        modal_composites, column_units, column_descriptions = dynamic_load_modal_composites(model_file, **filters)
        plot_modal_composite(modal_composites, column_units, column_descriptions)

        pdf.savefig()
        plt.close() # Prevents memory leaks

def configure_matplotlib():
    matplotlib.rc('figure',
        figsize=FIGURE_SIZE,
        titlesize='xx-large'
    )

    matplotlib.rc('figure.subplot',
        left   = 0.07, # the left side of the subplots of the figure
        right  = 0.98, # the right side of the subplots of the figure
        bottom = 0.06, # the bottom of the subplots of the figure
        top    = 0.91, # the top of the subplots of the figure
        wspace = 0.16, # the amount of width reserved for blank space between subplots
        hspace = 0.20, # the amount of height reserved for white space between subplots
    )

    matplotlib.rc('legend',
        fontsize='small',
    )

def main():
    # Setup command line option parser
    parser = argparse.ArgumentParser(
        description='Strip thickness-dependent vibration analysis and visualization '\
                    'of the parametric model of buckling and free vibration '\
                    'in prismatic shell structures, as computed by the '\
                    'fsm_eigenvalue project.',
    )
    parser.add_argument(
        'model_file',
        help="File storing the computed parametric model"
    )
    parser.add_argument(
        '-r',
        '--report_file',
        metavar='FILENAME',
        help="Store the analysis report to the selected FILENAME, uses '<model_file>.pdf' by default"
    )
    parser.add_argument(
        '--t_b-min',
        metavar='VAL',
        type=float,
        help='If specified, clip the minimum base strip thickness [mm] to VAL'
    )
    parser.add_argument(
        '--t_b-max',
        metavar='VAL',
        type=float,
        help='If specified, clip the maximum base strip thickness [mm] to VAL'
    )
    parser.add_argument(
        '--a',
        metavar='VAL',
        type=float,
        default=DEFAULT_A,
        help="Plot figures by fixing the selected strip length [mm] to VAL, %f by default" % DEFAULT_A
    )
    parser.add_argument(
        '-q',
        '--quiet',
        action='store_const',
        const=logging.WARN,
        dest='verbosity',
        help='Be quiet, show only warnings and errors'
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_const',
        const=logging.DEBUG,
        dest='verbosity',
        help='Be very verbose, show debug information'
    )
    parser.add_argument(
        '--version',
        action='version',
        version="%(prog)s " + __version__
    )
    args = parser.parse_args()

    # Configure logging
    log_level = args.verbosity or logging.INFO
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    configure_matplotlib()

    if not args.report_file:
        args.report_file = os.path.splitext(args.model_file)[0] + '.pdf'

    analyze_model(
        model_file=args.model_file,
        report_file=args.report_file,
        t_b_min=args.t_b_min,
        t_b_max=args.t_b_max,
        a_fix=args.a,
    )

if __name__ == '__main__':
    main()
