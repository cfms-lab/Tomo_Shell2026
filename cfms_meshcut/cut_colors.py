import numpy as np
DefaultFilamentColors = [
  '#a96fc4','#c6a446','#7a2b99','#d3881b','#512f10',
  '#e73b14','#1cb8ae','#d8fff6','#ff785f','#b01414',
  '#f5c600','#d8460b','#c21703','#9b4923','#007291',
	'#057CDD','#777777',"#0C7740",'#333333','#FFA500',
	'#107a00','#00777a','#001683','#FFFF00','#4B0082',
	'#aa5500','#999900','#ff0000','#00FF00','#0000FF']
DefaultFilamentColors = ['#ffffff', '#057CDD', "#0C7740",'#b01414','#4B0082','#555555']

TomoPixelColors    = [   '#808080',  '#8080ff',  '#ff0000',   '#FFA500',
	'#ff0055',    '#0000ff',   '#808080',    '#ff1100',
	'#ff0000', '#f4a460',   '#00FFFF']
RainbowColors = ['#FF0000', '#FFA500','#FFFF00','#008000','#0000FF', '#4B0082']


def hex_to_rgb(hex_code):
    """
    https://www.google.com/search?q=python+hex+string+to+color&oq=python+hex+string+to+color&gs_lcrp=EgZjaHJvbWUyCAgAEEUYFRg5MgYIARBFGDzSAQg0NTY1ajBqN6gCALACAA&sourceid=chrome&ie=UTF-8
    """
    hex_code = hex_code.lstrip('#')  # Remove '#' if present
    if len(hex_code) == 3:  # Handle shorthand hex codes like "#F00"
        hex_code = ''.join([c*2 for c in hex_code])

    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)
    return (r, g, b)

class cutColorSpan:
	n_color = 0
	colors = []

	def __init__(self, colors = DefaultFilamentColors):
		self.colors = colors
		self.n_color = len(self.colors)

	def get_color_float(self, index):
		(r,g,b) = hex_to_rgb( self.colors[index % self.n_color])
		return (np.array([r,g,b]) / 255.)

	def get_color_uint8(self, index):
		(r,g,b) = hex_to_rgb( self.colors[index % self.n_color])
		return (np.array([r,g,b]).astype(np.uint8))

	def get_color_str(self, index):
		return self.colors[index % self.n_color].lstrip('#')
