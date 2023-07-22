import time
import gradio as gr

# Extension Library
from library.download import DownloadManager

# Extension UI
from library.ui import html_blocks

# Download Manager instance
MANAGER = DownloadManager.instance()

def stop_state():
	return 'Stop Download' if MANAGER.running else 'Close Manager'

def run_start_download():
	while MANAGER.running:
		yield html_blocks.create_manager(MANAGER.files), stop_state()
		time.sleep(0.2)
	yield html_blocks.create_manager(MANAGER.files), stop_state()

def run_stop_download():
	MANAGER.stop()
	return html_blocks.create_manager(MANAGER.files), stop_state()

def component():
	''' Download Manager component '''

	with gr.Accordion('Download Manager', visible= False, elem_id= 'sd_mm_download_manager'):
		with gr.Column():
			html = gr.HTML()
			start = gr.Button(visible= False, elem_id= 'sd_mm_download_manager_start')
			stop = gr.Button(stop_state, elem_id= 'sd_mm_download_manager_stop')

	# Events
	start.click(run_start_download, outputs= [html, stop])
	stop.click(run_stop_download, outputs= [html, stop])