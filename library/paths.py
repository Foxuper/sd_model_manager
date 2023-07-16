from pathlib import Path

# SD Webui Modules
from modules import shared
import modules.scripts as scripts

# Directories
ROOT_DIR      = Path.cwd()
EXTENSION_DIR = Path(scripts.basedir())
IMAGES_DIR    = EXTENSION_DIR / 'images'
DATABASE_DIR  = EXTENSION_DIR / 'database'
TEMPLATES_DIR = EXTENSION_DIR / 'templates'

# Files
LOGGER_FILE    = EXTENSION_DIR / 'extension.log'
SCANNED_FILE   = EXTENSION_DIR / 'scanned.json'
LOCAL_MD_FILE  = TEMPLATES_DIR / 'local.md'
REMOTE_MD_FILE = TEMPLATES_DIR / 'remote.md'
VAE_MD_FILE    = TEMPLATES_DIR / 'vae.md'
LIST_MD_FILE   = TEMPLATES_DIR / 'list.md'

# Default SD web UI directories
CHECKPOINT_DIR   = ROOT_DIR / 'models/Stable-diffusion'
EMBEDDING_DIR    = ROOT_DIR / 'embeddings'
HYPERNETWORK_DIR = ROOT_DIR / 'models/hypernetworks'
LORA_DIR         = ROOT_DIR / 'models/Lora'
LYCORIS_DIR      = ROOT_DIR / 'models/LyCORIS'
VAE_DIR          = ROOT_DIR / 'models/VAE'

# Command line directories
CMD_CHECKPOINT_DIR   = 'ckpt_dir'
CMD_EMBEDDING_DIR    = 'embeddings_dir'
CMD_HYPERNETWORK_DIR = 'hypernetworks_dir'
CMD_LORA_DIR         = 'lora_dir'
CMD_LYCORIS_DIR      = 'lyco_dir'
CMD_VAE_DIR          = 'vae_dir'

def default_directory(type_name: str):
	''' Get the default directory for the given model type name '''

	if type_name == 'CHECKPOINT':
		return CHECKPOINT_DIR
	if type_name == 'EMBEDDING':
		return EMBEDDING_DIR
	if type_name == 'HYPERNETWORK':
		return HYPERNETWORK_DIR
	if type_name == 'LORA':
		return LORA_DIR
	if type_name == 'LYCORIS':
		return LYCORIS_DIR
	if type_name == 'VAE':
		return VAE_DIR
	raise ValueError(f'Invalid model type: {type_name}')

def custom_directory(type_name: str):
	''' Get the directory specified by the command line option for the given model type name '''

	def get_path(name: str):
		''' Get the path of the command line option with the given name '''
		if hasattr(shared.opts, name):
			option = getattr(shared.opts, name)
			return Path(option) if option is not None else None
		return None

	if type_name == 'CHECKPOINT':
		return get_path(CMD_CHECKPOINT_DIR)
	if type_name == 'EMBEDDING':
		return get_path(CMD_EMBEDDING_DIR)
	if type_name == 'HYPERNETWORK':
		return get_path(CMD_HYPERNETWORK_DIR)
	if type_name == 'LORA':
		return get_path(CMD_LORA_DIR)
	if type_name == 'LYCORIS':
		return get_path(CMD_LYCORIS_DIR)
	if type_name == 'VAE':
		return get_path(CMD_VAE_DIR)
	raise ValueError(f'Invalid model type: {type_name}')