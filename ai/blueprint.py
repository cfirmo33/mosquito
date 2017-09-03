import time
import pandas as pd
import configargparse
import core.common as common
from exchanges.exchange import Exchange


class Blueprint:
    """
    Main module for generating and handling datasets for AI
    """
    arg_parser = configargparse.get_argument_parser()
    arg_parser.add('--days', help='Days to start blueprint from', default=30)
    arg_parser.add('-f', '--features', help='Blueprints module name to be used to generated features', required=True)
    arg_parser.add('--ticker_size', help='Size of the candle ticker (minutes)', default=5)
    arg_parser.add('--pairs', help='Pairs to blueprint')
    arg_parser.add('-v', '--verbosity', help='Verbosity', action='store_true')
    arg_parser.add("--max_buffer_size", help="Maximum Buffer size (hours)", default=48)

    features_list = None
    exchange = None
    blueprint = None

    def __init__(self):
        args = self.arg_parser.parse_known_args()[0]
        self.ticker_size = int(args.ticker_size)
        self.start_time = int(time.time()) - int(args.days)*86400
        self.ticker_epoch = self.start_time
        self.exchange = Exchange(None)
        self.pairs = common.parse_pairs(self.exchange, args.pairs)
        blueprints_module = common.load_module('ai.blueprints.', args.features)
        self.blueprint = blueprints_module(self.pairs)
        self.max_buffer_size = int(args.max_buffer_size * (60 / self.ticker_size) * len(self.pairs))
        self.df_buffer = pd.DataFrame()
        self.df_blueprint = pd.DataFrame()

    @staticmethod
    def print_progress_dot(counter):
        """
        Prints progress
        """
        if counter % 100 == 0:
            print('.', end='', flush=True)
        if counter > 10000:
            counter = 0
            print('')
        return counter+1

    def write_to_file(self):
        """
        Writes df to file
        """
        # Remove not important columns
        print('\nProcessing done, total rows in dataset: ' + str(len(self.df_blueprint.index)))
        self.df_blueprint = self.df_blueprint.drop(['_id', 'id', 'curr_1', 'curr_2'], axis=1)
        filename = 'blueprint_' + self.blueprint.name + '_' + str(int(time.time())) + '.csv'
        self.df_blueprint.to_csv(filename, index=False)

    def run(self):
        """
        Calculates and stores dataset
        """
        dot_counter = 0
        while True:
            # Get new dataset
            df = self.exchange.get_offline_ticker(self.ticker_epoch, self.pairs)
            if df.empty:
                self.write_to_file()
                return

            # Store df to buffer
            self.df_buffer = self.df_buffer.append(df, ignore_index=True)
            self.df_buffer = common.handle_buffer_limits(self.df_buffer, self.max_buffer_size)

            scan_df = self.blueprint.scan(self.df_buffer, self.ticker_size)
            if not scan_df.empty:
                dot_counter = self.print_progress_dot(dot_counter)
                self.df_blueprint = self.df_blueprint.append(scan_df, ignore_index=True)

            self.ticker_epoch += self.ticker_size*60
