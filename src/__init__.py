# 1. Activar el entorno virtual venv\Scripts\activate
# 2. Ejecutar el script principal python src\__init__.py
# ------------------------------------------------------
import pefile
from tabulate import tabulate

import analystty

def print_tables(reorg, max_rows=10):
    keys = list(reorg.keys())
    for i in range(0, len(keys), max_rows):        
        chunk = {k: reorg[k] for k in keys[i:i + max_rows]}
        print(tabulate(chunk, headers='keys', tablefmt='grid'))
        print('\n')
def print_reorg(lists, key, value):
    reorg = {}
    for j in lists:
        for k in lists:
            if j[key] == k[key]:
                if j[key] not in reorg:
                    reorg[j[key]] = []
        # Idear un metodo para formatear de esta manera : 
        #reorg[j['START']].append(f"{j['NAME']}.{j['DLL']}\n\nrax : {j['AVA']}\n{j['INSTRUCTION']}")
        reorg[j[key]].append(j[value])
    print_tables(reorg, 7)

if __name__ == "__main__":
    pe = pefile.PE("data\\PE64\\test1.exe")
    
    '''
    test1 = analystty.frm_pe(pe)
    tlist = test1.getSections()  
    tlist = test1.getImports()
    tlist = test1.getMalApi()
    tlist = test1.getDisasm()
    tlist = test1.getInfoPe()
    
    print(tabulate(tlist, headers='keys', tablefmt="grid")) 
    '''

    # 
    '''
    lists = obj.getInfoPe()
    print(tabulate(lists, headers='keys', tablefmt="grid")) 

    lists = obj.getSections()
    print(tabulate(lists, headers='keys', tablefmt="grid")) 

    lists = obj.getDisasm()
    print(tabulate(lists, headers='keys', tablefmt="grid")) 
    '''

    #lists = obj.getFuncAddrs()
    #print('MATCHES')
    #print(tabulate(lists, headers='keys', tablefmt="grid")) 

    #lists = obj.getMalApi()
    #print('MALWARE APIs')
    #print(tabulate(lists, headers='keys', tablefmt="grid")) 

    #d = obj.getDisasm()
    #print('DISASM')
    #print(tabulate(d, headers='keys', tablefmt="grid")) 

    obj   = analystty.frm_pe(pe)

    #pe.print_info()
    lists = obj.getInfoPe()
    print(tabulate(lists, headers='keys', tablefmt='grid'))
    
    lists = obj.getSections()
    print(tabulate(lists, headers='keys', tablefmt='grid'))

    lists = obj.getImports()
    print(tabulate(lists, headers='keys', tablefmt='grid'))

    lists = obj.getFunctions()
    print(tabulate(lists, headers='keys', tablefmt='grid'))
    
    lists = obj.getMalApiDetect()
    print(tabulate(lists, headers='keys', tablefmt='grid'))

    lists = obj.getFunctionsByImports()
    print(tabulate(lists, headers='keys', tablefmt='grid'))

    lists = obj.getFunctionsByMalApiDetect()
    #print(tabulate(lists, headers='keys', tablefmt='grid'))
    print_reorg(lists, 'START', 'NAME')


    test = analystty.medbg(obj)
    for point in lists:
        ret = test.setBpList(int(point['ADDR'], 16))
        if ret:
            print(f'{point['NAME']}\t: OK')
        else:
            print('ERROR')

        
