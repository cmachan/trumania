from datagenerator.core import circus
import datagenerator.core.util_functions as util_functions
from datagenerator.core.actor import *


util_functions.setup_logging()

logging.info("building circus")

example1 = circus.Circus(
    name="example1",
    master_seed=12345,
    start=pd.Timestamp("1 Jan 2017 00:00"),
    step_duration=pd.Timedelta("1h"))

example1.run(
    duration=pd.Timedelta("48h"),
    log_output_folder="output/example1",
    delete_existing_logs=True
)
