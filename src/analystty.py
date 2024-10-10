import json
import pefile
import peutils

from capstone import *

import re

class frm_pe:
	def __init__(self, pe, config = 'DEFAULT'):
		self.__pe           = pe
		self.__config       = []
		self.__type         = 'PE64' if pe.FILE_HEADER.Machine == 0x8664 else 'PE32'
		self.__magic        = hex(pe.DOS_HEADER.e_magic) 
		self.__entrypoint   = pe.OPTIONAL_HEADER.AddressOfEntryPoint
				# Entry Point Address Virtual Allocation
		self.__ep_ava       = self.__entrypoint + pe.OPTIONAL_HEADER.ImageBase
		self.__basepointer  = 'rbp' if self.__type == 'PE64' else 'ebp'
		
		self.__sections     = []
		self.__imports      = []
		self.__malApiDetect = []
		self.__PeIdSign     = [] 
		self.__disasm       = []
		self.__mapMemory    = None
		self.__funcs        = []

		with open('src\\config.json', 'r') as f:
			data = json.load(f)
			self.__config = data[config]

		self.__getSections()
		self.__getImports()
		self.__getMalApiDetect()
		self.__getDisasm()
		self.__getFunctions()


	def __getSections(self):
		for section in self.__pe.sections:
			self.__sections.append({
				'VIRT_ADDR'         : hex(section.VirtualAddress),
				'RAW_ADDR'          : hex(section.PointerToRawData),
				'NAME'              : section.Name.decode('UTF-8').strip('\00'),
				'RAW_SIZE'          : section.SizeOfRawData,
				'VIRT_SIZE'         : section.Misc_VirtualSize,
				'CHARACTERISTICS'   : hex(section.Characteristics)  			
			})
	def __getImports(self):
		for entry in self.__pe.DIRECTORY_ENTRY_IMPORT:
			for imp in entry.imports:
				self.__imports.append({
					'ADDR' : hex(imp.address),
					'NAME' : imp.name.decode('UTF-8')  if imp.name else None,
					'DLL'  : entry.dll.decode('UTF-8') if imp.name else None
				})
	def __getMalApiDetect(self):
		with open(self.__config['MALAPI_PATH'], 'r') as f:
			data = json.load(f)
		for imp in self.__imports:
			tags = []
			for category, entries in data['Categories'].items():
				if imp['NAME'] in entries:
					tags.append(category)
			if tags:
				formatted_tags = ""
				for i, tag in enumerate(tags):
					formatted_tags += tag
					if (i+1) % 4 == 0 or i == len(tags) - 1:
						formatted_tags += "\n"
					else:
						formatted_tags += ", "
				self.__malApiDetect.append({
					'TAGS' : formatted_tags,
					'ADDR' : imp['ADDR'],
					'NAME' : imp['NAME'],
					'DLL'  : imp['DLL'],
				})
	def __getDisasm(self, sectionName = '.text'):
		for s in self.__sections:
			if s['NAME'] == sectionName:
				section = s
				break
			else:
				return None
		start = self.__pe.OPTIONAL_HEADER.ImageBase + int(section['VIRT_ADDR'], 16)
		end   = start + section['VIRT_SIZE'] - 1

		self.__mapMemory = self.__pe.get_memory_mapped_image()[self.__entrypoint:end]
		if self.__type == 'PE64':
			md = Cs(CS_ARCH_X86, CS_MODE_64)
		elif self.__type == 'PE32':
			md = Cs(CS_ARCH_X86, CS_MODE_32)
		else:
			print('Error es un archivo invalido')
			return None
		offset = 0
		for i in md.disasm(self.__mapMemory[offset:], self.__ep_ava + offset):
			if i.address == end:
				break
			opcodes  = ' '.join(f'{byte:02x}' for byte in i.bytes)
			self.__disasm.append({
				'ADDR'      : hex(i.address),
				'OPCODES'   : f'{opcodes:<20}',
				'MNEMONIC'  : f'{i.mnemonic}',
				'OPERATORS' : f'{i.op_str}'    
			})
			offset  += len(i.bytes)
	def __getFunctions(self):
		function_start_addr = 0x0
		function_end_addr   = 0x0 
		for disasm in self.__disasm:
			if disasm['MNEMONIC'] == 'push' and disasm['OPERATORS'] == self.__basepointer:
				function_start_addr = disasm['ADDR']
			elif disasm['MNEMONIC'] == 'ret':
				function_end_addr = disasm['ADDR']
			elif function_start_addr and function_end_addr != 0x0:
				self.__funcs.append({
					'START' : function_start_addr,
					'ARGS'  : None,
					'END'   : function_end_addr
				})
				function_start_addr = 0x0
				function_end_addr   = 0x0
	def getInfoPe(self):
		return[{
			'TYPE'        : self.__type, 
			'MAGIC'       : self.__magic,
			'ENTRY_POINT' : hex(self.__entrypoint),
			'EP_AVA'      : hex(self.__ep_ava)
		}]
	def __CalcOffsetFuncs(self):
		matches  = []
		previous = None
		start    = None
		for func in self.__funcs:
			for instruction in self.__disasm:
				address  = instruction['ADDR']
				mnemonic = instruction['MNEMONIC']
				operands = instruction['OPERATORS']
				
				if address == func['START']:
					start = address
				elif mnemonic == 'ret':
					start = None 
			
				if mnemonic in ['call', 'jmp']:
					if operands == 'rax':
						match = re.search(r'\[rip\s*([\+\-])\s*0x([0-9a-fA-F]+)\]', previous['OPERATORS'])
					else:
						match = re.search(r'\[rip\s*([\+\-])\s*0x([0-9a-fA-F]+)\]', operands)
					if match:
						offset = int(match.group(1) + match.group(2), 16)
						address = hex(int(address, 16) + offset)
						matches.append({
							'START'            : start,
							'ADDR_PREVIOUS'    : previous['ADDR'],
							'ADDR_INSTRUCTION' : instruction['ADDR'],
							'OFFSET'           : hex(offset),
							'ADDR_CALC'        : address,
							'INSTRUCTION'      : f"{previous['MNEMONIC']} {previous['OPERATORS']}\n{mnemonic} {operands}"
						})
					else:
						match = re.search(r'0x[0-9a-fA-F]+', operands)
						if match:
							offset  = None
							address = hex(int(match.group(), 16))
							matches.append({
								'START'            : start,
								'ADDR_PREVIOUS'    : previous['ADDR'],
								'ADDR_INSTRUCTION' : instruction['ADDR'],
								'OFFSET'           : offset,
								'ADDR_CALC'        : address,
								'INSTRUCTION'      : f"{mnemonic} {operands}"
							})
				previous = instruction
		return matches
	def getSections(self):
		return self.__sections
	def getImports(self):
		return self.__imports
	def getFunctions(self):
		return self.__funcs
	def getMalApiDetect(self):
		return self.__malApiDetect

		# Ordenar las importaciones dentro de las funciones que la usan 
	def getFunctionsByImports(self):
		funcsByImports = []
		funcs_calcs    = self.__CalcOffsetFuncs()
		for func_calc in funcs_calcs:
			if func_calc['START'] != None:
				funcsByImports.append(func_calc)
		return funcsByImports

		# Ordenar las importaciones relacionadas con el malware en las funciones que la usan
	def getFunctionsByMalApiDetect(self):
		funcsByMalApiOrdened = []
		funcs_calcs    = self.__CalcOffsetFuncs()
		for malapi in self.__malApiDetect:
			for func_calc in funcs_calcs: 
				if func_calc['START'] != None:
					if malapi['ADDR'] == func_calc['ADDR_CALC']:
						funcsByMalApiOrdened.append({
							'START'       : func_calc['START'],
							'ADDR'        : func_calc['ADDR_INSTRUCTION'],
							'INSTRUCTION' : func_calc['INSTRUCTION'],
							'AVA'   	  : func_calc['ADDR_CALC'],
							'NAME'        : malapi['NAME'],
							'DLL'         : malapi['DLL']
						})
		return funcsByMalApiOrdened



