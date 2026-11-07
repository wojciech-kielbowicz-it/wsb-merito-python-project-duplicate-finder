import hashlib
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List, Tuple

from core.decorators import measure_time, retry, requires_valid_root
from core.reader import FileChunkIterator
from core.walker import build_file_pipeline
