import json
import peutils

from capstone import *

import re

path = {
    'MALAPI' : "src\\malapi.json"    
}

class frm_pe:
    def __init__(self, pe):
        self.__type         = 'PE64' if pe.FILE_HEADER.Machine == 0x8664 else 'PE32' 
        self.__magic        = hex(pe.DOS_HEADER.e_magic) 
        self.__sections     = []
        self.__imports      = []
        self.__malApiDetect = []
        self.__PeIdSign     = [] 
        self.__disasm       = []
        # {'START' : *, 'ARGS' : *,'END' : *}
        self.__funcs_addr = []

        self.__getSections(pe)
        self.__getImports(pe)
        self.__getMalApiDetect(pe)
        self.__getPeIdSign(pe)
        self.__getDisasm(pe)

    def __getSections(self, pe):
        for section in pe.sections:
            self.__sections.append({
                'VIRT_ADDR'         : hex(section.VirtualAddress),
                'RAW_ADDR'          : hex(section.PointerToRawData),
                'NAME'              : section.Name.decode('UTF-8').strip('\00'),
                'RAW_SIZE'          : section.SizeOfRawData,
                'VIRT_SIZE'         : section.Misc_VirtualSize,
                'Characteristics'   : hex(section.Characteristics)
            })
    def __getImports(self, pe):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for imp in entry.imports:
                self.__imports.append({
                    'NAME'    : imp.name.decode('UTF-8') if imp.name else None,
                    'DLL'     : entry.dll.decode('UTF-8') if imp.name else None,
                    'ADDRESS' : hex(imp.address)
                })
    def __getMalApiDetect(self, pe):
        with open(path['MALAPI'], "r") as f:
            data = json.load(f)
        for imp in self.__imports:
            tags = []
            for category, entries in data["Categories"].items():
                if imp['NAME'] in entries:
                    tags.append(category)
            if tags:
                formatted_tags = ""
                for i, tag in enumerate(tags):
                    formatted_tags += tag
                    if(i+1) % 4 == 0 or i == len(tags) - 1:
                        formatted_tags += "\n"
                    else:
                        formatted_tags += ", "
                self.__malApiDetect.append({
                    'TAGS'     : formatted_tags,
                    'NAME'     : imp['NAME'],
                    'DLL'      : imp['DLL'],
                    'ADDRESS'  : hex(int(imp['ADDRESS'], 16))
                    })                
    def __getPeIdSign(self, pe):
        return None    
    def __getDisasm(self, pe, sectionName = '.text'):
        for s in self.__sections:
            if s['NAME'] == sectionName:
                section = s
                break
            else:
                return None
        
        ep      = pe.OPTIONAL_HEADER.AddressOfEntryPoint
        ep_ava  = ep + pe.OPTIONAL_HEADER.ImageBase

        start   = pe.OPTIONAL_HEADER.ImageBase + int(section['VIRT_ADDR'], 16)
        end     = start + section['VIRT_SIZE'] - 1

        data    = pe.get_memory_mapped_image()[ep:end]

        if(self.__type == 'PE64'):
            md  = Cs(CS_ARCH_X86, CS_MODE_64)
            bp  = 'rbp'
        else: 
            md  = Cs(CS_ARCH_X86, CS_MODE_32)
            bp  = 'ebp'
        offset  = 0

        
        function_start_addr = 0x0
        function_end_addr   = 0x0
        for i in md.disasm(data[offset:], ep_ava + offset):
            if i.address == end:
                break
            offset += len(i.bytes)
            opcodes = ' '.join(f'{byte:02x}' for byte in i.bytes)
            
            if i.mnemonic == 'push' and i.op_str == bp:
                function_start_addr = i.address
            elif i.mnemonic == 'ret':
                function_end_addr = i.address
            elif function_start_addr and function_end_addr != 0x0:
                self.__funcs_addr.append({
                    'START' : hex(function_start_addr),
                    'ARGS'  : None,
                    'END'   : hex(function_end_addr)
                })
                function_start_addr = 0x0
                function_end_addr   = 0x0

            self.__disasm.append({
                'FUNC_START_ADDR' : hex(function_start_addr),
                'ADDR'            : hex(i.address),
                'OPCODES'         : f'{opcodes:<20}',
                'MNEMONIC'        : f'{i.mnemonic}',
                'OPERATORS'       : f'{i.op_str}'
            })
    def getInfoPe(self):
        return [{'TYPE' : self.__type, 'MAGIC' : self.__magic}] 

    def getSections(self):
        return self.__sections

    def getImports(self):
        return self.__imports

    def getMalApi(self):
        return self.__malApiDetect

    def getPeIdSign(self):
        return self.__PeIdSign

    def getDisasm(self):
        return self.__disasm

    def getFuncs(self):
        return self.__funcs_addr

    #mov  rax, qword ptr [rip + 0x6e55] 
    # Para calcular esto necesito la direccion rip (de la instruccion del call) y sumarle el valor
    # esto me dara la direccion en donde esta ubicada la direccion exportada
    #call rax    
    def getFuncAddrs(self):
        matches = []

        previous = None
        for instruction in self.__disasm:
            mnemonic = instruction['MNEMONIC']
            operands = instruction['OPERATORS']

            # Considerar más instrucciones relevantes
            if mnemonic in ['call', 'jmp']:
                if operands == 'rax':
                    match = re.search(r'\[rip\s*([\+\-])\s*0x([0-9a-fA-F]+)\]', previous['OPERATORS'])
                else:          
                    # Regex más flexible para capturar direcciones y offsets
                    match = re.search(r'\[rip\s*([\+\-])\s*0x([0-9a-fA-F]+)\]', operands)
                if match:
                    offset = int(match.group(1) + match.group(2), 16)
                    # Calcular la dirección real considerando el offset
                    address = hex(int(instruction['ADDR'], 16) + offset)
                    matches.append({
                        'ADDR'        : instruction['ADDR'],
                        'INSTRUCTION' : f'{instruction['MNEMONIC']} {instruction['OPERATORS']}',
                        'CALC_ADDR'   : address

                    })
                else:
                    # Buscar direcciones simples
                    match = re.search(r'0x[0-9a-fA-F]+', operands)
                    if match:
                        address= hex(int(match.group(), 16))
                        for start in self.__funcs_addr:
                            if instruction['ADDR']: 
                                matches.append({
                                    'START'       : instruction['FUNC_START_ADDR'],
                                    'ADDR'        : instruction['ADDR'],
                                    'INSTRUCTION' : f'{instruction['MNEMONIC']} {instruction['OPERATORS']}',
                                    'CALC_ADDR'   : address
                                })
            previous = instruction

        return matches

    def getFuncImportUsed(self):
        matches    = []
        ADDRS = self.getFuncAddrs()
        for malapi in self.__malApiDetect:
            for addr in ADDRS:
                print(f"{addr['ADDR']} : {addr['CALC_ADDR']} -- {malapi['ADDRESS']} | {addr['INSTRUCTION']}")
                if addr['CALC_ADDR'] == malapi['ADDRESS']:
                    for funcs_addr in self.__funcs_addr:
                        #print(f"{ADDRS['START']} {funcs_addr['START']}")
                        if ADDRS['START'] == funcs_addr['START']:
                            matches.append({
                                'START' : funcs_addr['START'],
                                'END'   : funcs_addr['END'],
                                'NAME'  : malapi['NAME'],
                                'DLL'   : malapi['DLL']
                            })
