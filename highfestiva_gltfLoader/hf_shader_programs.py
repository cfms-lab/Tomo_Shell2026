from glm import mat4
from pathlib import Path

class ShaderPrograms:
	def __init__(self, shader_dir, shader_names, ctx, textures):
		self.shader_dir = shader_dir
		self.ctx = ctx  #OpenGL context to draw on
		self.textures = textures # list of texture ID's
		self.shaders = {} # stands for "shader programs"
		self.shader_names = shader_names# list of shader names; {'simple','shadow', ... }

	def update_uniforms(self, shader, current_camera):
		proj_mat = current_camera.get_projection()
		view_mat = current_camera.get_view()
		shader['m_proj'].write(proj_mat)
		shader['m_view'].write(view_mat)
		shader['m_model'].write(mat4())

	def get(self, shader_name):
		return self.shaders[shader_name]

	def load_shader(self, ctx, curr_shader_name):
		vs = Path(self.file_resolve(f'{self.shader_dir}{curr_shader_name}.vert')).read_text()
		fs = Path(self.file_resolve(f'{self.shader_dir}{curr_shader_name}.frag')).read_text()
		shader = ctx.program(vertex_shader = vs, fragment_shader = fs)
		self.shaders[curr_shader_name] = shader
		return shader

	def load_all(self):
		self.release()
		for name in self.shader_names:
			self.load_shader(ctx = self.ctx, curr_shader_name = name)

	def release(self):
		for c_sh in self.shaders.values():
			c_sh.release()
		self.shaders.clear()

	def file_resolve(self, filename):
		return filename
