import numpy as np
from collections import namedtuple
from pathlib import Path
import cv2

TextureInfo = namedtuple('TextureInfo', 'dir bufferViewID gltfBufferView mimeType name uri')

class hfTextures:
	def __init__(self, renderer, _texture_infos : TextureInfo):
		self.renderer = renderer
		self.tex_data = {} #dictionary name/texture
		for ti in _texture_infos:
			(tex_name, tex_data)	= self.load( ti)
			self.tex_data[tex_name] = tex_data

	def load( self, ti: TextureInfo):
		is_3d = False
		assert ti.uri is not None
		import os
		tex_name,ext = os.path.splitext(ti.uri)
		full_fname = self.file_resolve(f'{ti.dir}\\{tex_name}{ext}')
		cv_img = cv2.imread(full_fname, cv2.IMREAD_COLOR)
		cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
		texture_data = np.asarray(cv_img, dtype=np.float32) / 255.#(width, height, color=[0,1] x3)
		return (tex_name, texture_data)

	def get(self, name):
		return self.tex_data[name]

	def file_resolve(self, filename):
		return filename


