from xml.etree import ElementTree as ET
from xml.dom import minidom
from collections import Counter, defaultdict
from pathlib import Path

O=Path('/mnt/data/logisim_entrega'); O.mkdir(exist_ok=True)
p=ET.Element('project',{'source':'5.0.0','version':'1.0'})
p.text='\n  Diseño académico Harvard monociclo de 16 bits, prototipo pendiente de simulación en GUI.\n'
for i,desc in enumerate(['#Wiring','#Gates','#Plexers','#Arithmetic','#FPArithmetic','#Memory','#I/O','#Base']): ET.SubElement(p,'lib',{'name':str(i),'desc':desc})
ET.SubElement(p,'main',{'name':'CPU16'})
opts=ET.SubElement(p,'options')
for name,val in [('gateUndefined','ignore'),('simlimit','1000'),('simrand','0')]: ET.SubElement(opts,'a',{'name':name,'val':val})
ET.SubElement(p,'mappings'); tb=ET.SubElement(p,'toolbar')
for lib,name in [('7','Poke Tool'),('7','Edit Tool'),('7','Text Tool'),('0','Pin'),('0','Splitter'),('0','Tunnel'),('5','Register'),('2','Multiplexer')]: ET.SubElement(tb,'tool',{'lib':lib,'name':name})

def xy(x,y): return f'({x},{y})'

def attr(node, **kw):
 for k,v in kw.items(): ET.SubElement(node,'a',{'name':k,'val':str(v).lower() if isinstance(v,bool) else str(v)})
 return node

class Circuit:
 def __init__(self,name,inputs=None,outputs=None):
  self.name=name; self.inputs=inputs or [];self.outputs=outputs or []
  self.el=ET.SubElement(p,'circuit',{'name':name}); attr(self.el,circuit=name)
  self.components=[]
  # Input and output ports are visualized as labelled pins at left and right of each schematic.
  for i,(s,w) in enumerate(self.inputs):
   self.pin(s,w,80,80+i*50,False)
  for i,(s,w) in enumerate(self.outputs):
   self.pin(s,w,1400,80+i*50,True)
  if inputs is not None or outputs is not None:
   a=ET.SubElement(self.el,'appear')
   height=max(100, max(len(self.inputs),len(self.outputs))*20+40)
   ET.SubElement(a,'rect',{'fill':'none','height':str(height),'stroke':'#202b3c','stroke-width':'2','width':'180','x':'50','y':'40'})
   ET.SubElement(a,'text',{'font-family':'SansSerif','font-size':'12','font-weight':'bold','text-anchor':'middle','x':'140','y':'53'}).text=name
   for i,(s,w) in enumerate(self.inputs):
    y=60+i*20
    ET.SubElement(a,'circ-port',{'height':'8','pin':f'80,{80+i*50}','width':'8','x':'46','y':str(y-4)})
   for i,(s,w) in enumerate(self.outputs):
    y=60+i*20
    ET.SubElement(a,'circ-port',{'height':'10','pin':f'1400,{80+i*50}','width':'10','x':'225','y':str(y-5)})
   ET.SubElement(a,'circ-anchor',{'facing':'east','height':'6','width':'6','x':'227','y':'57'})
 def c(self,lib,name,x,y,**kw):
  o=ET.SubElement(self.el,'comp',{'lib':str(lib),'loc':xy(x,y),'name':name})
  for key,value in kw.items():
   if key=='contents': ET.SubElement(o,'a',{'name':'contents'}).text=str(value)
   else: attr(o,**{key:value})
  self.components.append((lib,name,x,y,kw))
  return o
 def t(self,name,w,x,y,facing='east'):
  return self.c(0,'Tunnel',x,y,label=name,width=w,facing=facing)
 def pin(self,name,w,x,y,output):
  self.c(0,'Pin',x,y,label=name,width=w,**({'output':'true','facing':'west'} if output else {'facing':'east'}))
  self.t(name,w,x,y,'west' if not output else 'east')
 def const(self,value,width,x,y):
  self.c(0,'Constant',x,y,width=width,value=hex(value));return x,y
 def wire(self,fromx,fromy,tox,toy):
  assert fromx==tox or fromy==toy, (fromx,fromy,tox,toy)
  ET.SubElement(self.el,'wire',{'from':xy(fromx,fromy),'to':xy(tox,toy)})
 def gate(self,kind,opname,width,x,y,a,b,sz=50):
  self.c(1,kind+' Gate',x,y,width=width,size=sz,inputs=2)
  self.t(a,width,x-50,y-20);self.t(b,width,x-50,y+20)
  self.t(opname,width,x,y,'west')
 def inverter(self,name_in,name_out,width,x,y):
  self.c(1,'NOT Gate',x,y,width=width)
  self.t(name_in,width,x-30,y);self.t(name_out,width,x,y,'west')
 def add(self,a,b,ci,result,cout,w,x,y):
  self.c(3,'Adder',x,y,width=w)
  self.t(a,w,x-40,y-10);self.t(b,w,x-40,y+10)
  self.t(ci,1,x-20,y-20);self.t(result,w,x,y,'west');self.t(cout,1,x-20,y+20,'west')
 def compare(self,a,b,eq,w,x,y):
  self.c(3,'Comparator',x,y,width=w)
  self.t(a,w,x-40,y-10);self.t(b,w,x-40,y+10)
  self.t(eq,1,x,y,'west')
 def mux(self,name,inputs,sel,width,x,y):
  bits={2:1,4:2}[len(inputs)];self.c(2,'Multiplexer',x,y,width=width,select=bits,enable='false')
  if len(inputs)==2:
   for idx,lab in enumerate(inputs): self.t(lab,width,x-30,y+(-10 if idx==0 else 10))
  else:
   for idx,lab in enumerate(inputs): self.t(lab,width,x-40,y-20+idx*10)
  self.t(sel,bits,x-20,y+20);self.t(name,width,x,y,'west')
 def split(self,inputname,input_w,outpairs,x,y,faces='east'):
  # outpairs: list of (name,width), defines contiguous ascending bits.
  assert sum(w for _,w in outpairs)==input_w
  n=len(outpairs); attrs=dict(fanout=n,incoming=input_w,facing=faces)
  k=0
  for i,(_,w) in enumerate(outpairs):
   for j in range(w): attrs['bit'+str(k)]=i;k+=1
  self.c(0,'Splitter',x,y,**attrs)
  self.t(inputname,input_w,x,y,'east' if faces=='west' else 'west')
  for i,(lab,w) in enumerate(outpairs):
   if faces=='east': yy=y-(n-i)*10;xx=x+20
   else: yy=y+(i+1)*10;xx=x-20
   if lab: self.t(lab,w,xx,yy,'west' if faces=='east' else 'east')
 def splitmapped(self,inputname,input_w,outs,mapping,x,y,faces='east'):
  # mapping bit -> port index, outs array (label,width); can duplicate input data (high sign bit via one port)
  n=len(outs);attrs=dict(fanout=n,incoming=input_w,facing=faces)
  for b,k in enumerate(mapping): attrs['bit'+str(b)]=k
  self.c(0,'Splitter',x,y,**attrs)
  self.t(inputname,input_w,x,y,'east' if faces=='west' else 'west')
  for i,(lab,w) in enumerate(outs):
   if faces=='east': yy=y-(n-i)*10;xx=x+20
   else: yy=y+(i+1)*10;xx=x-20
   if lab:self.t(lab,w,xx,yy,'west' if faces=='east' else 'east')
 def sub(self,name,x,y,inputs,outputs,labels=None):
  self.el.append(ET.Element('comp',{'loc':xy(x,y),'name':name}))
  # ports: x-180, y+20i (inputs), x,y+20i (outputs)
  for i,(lab,w) in enumerate(inputs): self.t(lab,w,x-180,y+i*20)
  for i,(lab,w) in enumerate(outputs): self.t(lab,w,x,y+i*20,'west')

# Build sign extenders with 2 splitters; most significant bit is repeated using a merged bus.
def signext(n):
 c=Circuit(f'SEXT{n}', [('IN',n)],[('OUT',16)])
 c.split('IN',n,[(f's{i}',1) for i in range(n)],280,250)
 # merge: in 16-bit bus, bits <n each one end, higher all driven by sign bit on last end
 mapping=list(range(16))
 c.splitmapped('OUT',16,[(f's{i if i < n else n-1}',1) for i in range(16)],mapping,760,350,'west')
 return c
signext(8);signext(12)

# Arithmetic/logic unit, 16 bit, with Z/N/C/V packed as bits 0..3.
a=Circuit('ALU16',[('A',16),('B',16),('OP',2)],[('Y',16),('FLAGS',4)])
a.split('OP',2,[('op0',1),('op1',1)],280,200)
a.inverter('op1','not_op1',1,400,200)
a.gate('AND','sub',1,500,200,'op0','not_op1')
a.inverter('B','NOT_B',16,400,360)
a.mux('B_mod',['B','NOT_B'],'sub',16,610,360)
a.add('A','B_mod','sub','SUM','Cout',16,800,360)
a.gate('AND','AND16',16,620,500,'A','B')
a.gate('OR','OR16',16,620,600,'A','B')
a.mux('Y',['SUM','SUM','AND16','OR16'],'OP',16,980,440)
a.const(0,16,1030,620);a.t('ZERO16',16,1030,620,'west')
a.compare('Y','ZERO16','z',16,1100,620)
for sig,y in [('Y',750),('A',830),('B',910)]:
 a.splitmapped(sig,16,[(None,15),(sig+'_msb',1)],[0]*15+[1],1120,y)
a.gate('XOR','xab',1,1290,840,'A_msb','B_msb')
a.gate('XOR','xay',1,1290,940,'A_msb','Y_msb')
a.gate('XNOR','same_or_diff',1,1460,840,'xab','sub')
a.gate('AND','v_ungated',1,1620,880,'same_or_diff','xay')
a.gate('AND','v',1,1790,900,'v_ungated','not_op1')
a.gate('XOR','c_pre',1,1290,1040,'Cout','sub')
a.gate('AND','c',1,1460,1040,'c_pre','not_op1')
# N=Y[15]. Merge flags [Z,N,C,V] using splitter facing west.
a.split('FLAGS',4,[('z',1),('Y_msb',1),('c',1),('v',1)],1880,1200,'west')

# Register bank: 12 physical registers R4..R15, 2 combinational read ports.
regs=Circuit('REGS12', [('CLK',1),('RESET',1),('WE',1),('WA',4),('WD',16),('RA',4),('RB',4)], [('QA',16),('QB',16),('R4',16)])
# Decoder 4x16 uses address at origin, enable at (x-10,y), output ports (x+20,y-160..y-10).
regs.c(2,'Decoder',360,250,select=4,enable='true')
regs.t('WA',4,360,250);regs.t('WE',1,350,250)
for idx in range(4,16):
 regs.t(f'en{idx}',1,380,250-(16-idx)*10,'west')
 ry=100+(idx-4)*140
 regs.c(5,'Register',600,ry,width=16,label=f'R{idx}')
 regs.t('WD',16,600,ry+30);regs.t(f'en{idx}',1,600,ry+50)
 regs.t('CLK',1,600,ry+70);regs.t('RESET',1,630,ry+90)
 regs.t(f'R{idx}',16,660,ry+30,'west')
# address splitter lower2 upper2, fanout2 positions
regs.split('RA',4,[('RAlo',2),('RAhi',2)],850,200)
regs.split('RB',4,[('RBlo',2),('RBhi',2)],850,900)
regs.const(0,16,1040,120);regs.t('ZERO16',16,1040,120,'west')
for pfx,low,high,base in [('A','RAlo','RAhi',300),('B','RBlo','RBhi',1040)]:
 for grp in range(4):
  values=[('ZERO16' if grp==0 else f'R{grp*4+i}') for i in range(4)]
  regs.mux(f'{pfx}{grp}',values,low,16,1120,base+grp*140)
 regs.mux('QA' if pfx=='A' else 'QB',[f'{pfx}{i}' for i in range(4)],high,16,1320,base+220)
# R4 output already tunneled in bank => external port same label R4.

# Register-based SRAM 16 x 16 with asynchronous read, full 16-bit logical address.
ram=Circuit('RAM16_ASYNC', [('CLK',1),('ADDR',16),('DIN',16),('WE',1)], [('DOUT',16),('M0',16)])
ram.split('ADDR',16,[('Alo',4),('Ahi',12)],300,160)
ram.const(0,12,380,380);ram.t('ZERO12',12,380,380,'west')
ram.compare('Ahi','ZERO12','ADDR_OK',12,500,380)
ram.gate('AND','MEMWE',1,660,400,'WE','ADDR_OK')
ram.c(2,'Decoder',760,320,select=4,enable='true');ram.t('Alo',4,760,320);ram.t('MEMWE',1,750,320)
for idx in range(16):
 ram.t(f'wen{idx}',1,780,320-(16-idx)*10,'west')
 ry=100+idx*120
 ram.c(5,'Register',1000,ry,width=16,label=f'M{idx}')
 ram.t('DIN',16,1000,ry+30);ram.t(f'wen{idx}',1,1000,ry+50)
 ram.t('CLK',1,1000,ry+70)
 ram.const(0,1,1030,ry+90)  # RAM persists across reset (no clear)
 ram.t(f'M{idx}',16,1060,ry+30,'west')
ram.split('Alo',4,[('A0',2),('A1',2)],1110,300)
for grp in range(4):
 ram.mux(f'G{grp}',[f'M{grp*4+i}' for i in range(4)],'A0',16,1210,300+grp*140)
ram.mux('MUX_READ',[f'G{i}' for i in range(4)],'A1',16,1350,520)
ram.const(0,16,1240,760);ram.t('ZERO16',16,1240,760,'west')
ram.inverter('ADDR_OK','ADDR_BAD',1,1300,800)
ram.mux('DOUT',['MUX_READ','ZERO16'],'ADDR_BAD',16,1450,820)
# M0 output tunnel above uses same M0 label as actual register

# Table driven decoder (16 words).  Packed CTL = bits:
# 0:DestSel 1:ALUSrc 2..3:ALUOp 4..5:WBSel
# 6:RW 7:MemRead 8:MW 9:FW 10..11:BranchKind
# 12:IsR 13:IsI 14:IsJ 15:ValidOp (only opcode 0..C)
rows=[]
ops = [
 (0,0,0,0,1,0,0,1,0),  #ADD
 (0,0,1,0,1,0,0,1,0),  #SUB
 (0,0,2,0,1,0,0,1,0),  #AND
 (0,0,3,0,1,0,0,1,0),  #OR
 (0,0,1,0,0,0,0,1,0),  #CMP
 (0,0,0,1,1,0,0,0,0),  #MOV_R
 (0,0,0,2,1,1,0,0,0),  #LOAD
 (0,0,0,0,0,0,1,0,0),  #STORE
 (1,0,0,3,1,0,0,0,0),  #MOV_I
 (1,1,0,0,1,0,0,1,0),  #ADD_I
 (0,0,0,0,0,0,0,0,1),  #JZ
 (0,0,0,0,0,0,0,0,2),  #JNZ
 (0,0,0,0,0,0,0,0,3),  #JMP
]
for op in range(16):
 if op>=13:rows.append(0);continue
 d,src,alu,wb,rw,mr,mw,fw,bk=ops[op]
 val=(d)|(src<<1)|(alu<<2)|(wb<<4)|(rw<<6)|(mr<<7)|(mw<<8)|(fw<<9)|(bk<<10)
 val|=(1<< (12 if op<=7 else 13 if op<=9 else 14)) | (1<<15)
 rows.append(val)
control=Circuit('CONTROL',[('IR',16),('Z_REG',1)], [('DestSel',1),('ALUSrc',1),('ALUOp',2),('WBSel',2),('RegWrite',1),('MemRead',1),('MemWrite',1),('FlagWrite',1),('BranchTaken',1),('ValidInstr',1)])
control.split('IR',16,[("NIB",4),("RDR",4),("RS",4),("OP",4)],300,300)
# ROM has input at (x,y+10) and output at (x+240,y+60)
control.c(5,'ROM',700,180,addrWidth=4,dataWidth=16,contents='addr/data: 4 16\n'+' '.join(f'{row:x}' for row in rows)+'\n',label='ControlROM')
control.t('OP',4,700,190);control.t('RAW_CTL',16,940,240,'west')
# Break control ROM word into 16 1-bit outputs.
control.split('RAW_CTL',16,[(f'p{i}',1) for i in range(16)],1000,480)
# Reg validation comparators width4 against 4; comparator LT output (x,y+10).
control.const(4,4,1120,60);control.t('CONST4',4,1120,60,'west')
control.c(3,'Comparator',1170,200,width=4,mode='unsigned')
control.t('RS',4,1130,190);control.t('CONST4',4,1130,210)
control.t('RS_GT',1,1170,190,'west') # greater pin
control.t('RS_EQ',1,1170,200,'west')
control.gate('OR','RS_VALID',1,1270,200,'RS_GT','RS_EQ')
control.c(3,'Comparator',1170,320,width=4,mode='unsigned')
control.t('RDR',4,1130,310);control.t('CONST4',4,1130,330)
control.t('RDR_GT',1,1170,310,'west');control.t('RDR_EQ',1,1170,320,'west')
control.gate('OR','RDR_VALID',1,1270,320,'RDR_GT','RDR_EQ')
control.const(0,4,1120,430);control.t('ZERO4',4,1120,430,'west')
control.compare('NIB','ZERO4','NIB_ZERO',4,1200,440)
control.gate('AND','BOTH_REGS',1,1360,340,'RS_VALID','RDR_VALID')
control.gate('AND','VALID_R_FIELDS',1,1470,340,'BOTH_REGS','NIB_ZERO')
control.gate('AND','VALID_R',1,1580,340,'VALID_R_FIELDS','p12')
control.gate('AND','VALID_I',1,1580,430,'RS_VALID','p13')
# VALID_J p14; Valid= OR3 from OR+OR
control.gate('OR','VALID_RI',1,1690,350,'VALID_R','VALID_I')
control.gate('OR','ValidInstr',1,1800,390,'VALID_RI','p14')
# Expose scalar selectors by short wire stubs; valid bit is not required for selectors
# because when invalid, all write enables and branches are disabled.
for k,lab in [(0,'DestSel'),(1,'ALUSrc')]:
 y=510+k*60
 control.t(f'p{k}',1,1700,y); control.t(lab,1,1760,y,'west'); control.wire(1700,y,1760,y)
control.split('ALUOp',2,[('p2',1),('p3',1)],1880,650,'west')
control.split('WBSel',2,[('p4',1),('p5',1)],1880,720,'west')
for ix,lab in [(6,'RegWrite'),(7,'MemRead'),(8,'MemWrite'),(9,'FlagWrite')]:
 y=850+(ix-6)*90
 control.gate('AND',lab,1,1960,y,f'p{ix}','ValidInstr')
# branching from p10 = kind0, p11 = kind1, equivalent to JMP or JZ and Z or JNZ and not Z.
control.inverter('Z_REG','NOTZ',1,1900,1250)
control.gate('AND','BK_BOTH',1,2050,1280,'p10','p11')
control.gate('AND','BK_Z',1,2050,1380,'p10','Z_REG')
control.gate('AND','BK_NOTZ',1,2050,1480,'p11','NOTZ')
control.gate('OR','BK_OR',1,2200,1330,'BK_BOTH','BK_Z')
control.gate('OR','BK_ANY',1,2340,1430,'BK_OR','BK_NOTZ')
control.gate('AND','BranchTaken',1,2490,1430,'BK_ANY','ValidInstr')

# Entire CPU: only state updates on rising edge.  DATA RAM is asynchronous register array.
# PC16 + ROM16 ROM address width 16, so PC represents word addresses, no truncation.
cpu=Circuit('CPU16')
for name,w,y in [('CLK',1,100),('RESET',1,150),('RUN',1,200),('DBG_ADDR',16,310),('DBG_DIN',16,360),('DBG_WRITE',1,410)]:
 cpu.pin(name,w,80,y,False)
for name,w,y in [('PC',16,100),('IR',16,160),('R4',16,220),('FLAGS',4,280),('RAM0',16,340),('VALID',1,400)]:
 cpu.pin(name,w,3020,y,True)
# PC state
cpu.c(5,'Register',320,620,width=16,label='PC')
cpu.t('NEXT_PC',16,320,650);cpu.t('RUN',1,320,670)
cpu.t('CLK',1,320,690);cpu.t('RESET',1,350,710)
cpu.t('PC',16,380,650,'west')
# Program ROM: one 16-bit word per PC address.
rom_words=[0x8400,0x8564,0x8700,0x880A,0x6760,0x4560,0xA006,0x9401,0x9701,0x4840,0xBFFA,0xC000,0xC000]
rom_content='addr/data: 16 16\n'+' '.join(f'{w:04x}' for w in rom_words)+'\n'
cpu.c(5,'ROM',580,560,addrWidth=16,dataWidth=16,contents=rom_content,label='Programa 13 instrucciones')
cpu.t('PC',16,580,570);cpu.t('IR',16,820,620,'west')
# IR fields
cpu.split('IR',16,[('NIB',4),('RD_R',4),('RS',4),('OPCODE',4)],960,620)
cpu.split('IR',16,[('IMM8',8),('DROP8',8)],960,800)
cpu.split('IR',16,[('OFFSET12',12),('DROP4',4)],960,920)
cpu.sub('SEXT8',1290,830,[('IMM8',8)],[('IMM16',16)])
cpu.sub('SEXT12',1290,960,[('OFFSET12',12)],[('OFF16',16)])
# CONTROL inputs from IR and stored Z, outputs in declared order.
cpu.sub('CONTROL',1500,140,[('IR',16),('Z_REG',1)], [('DestSel',1),('ALUSrc',1),('ALUOp',2),('WBSel',2),('RegWrite',1),('MemRead',1),('MemWrite',1),('FlagWrite',1),('BranchTaken',1),('VALID',1)])
# Mux to select Rd field depending on format
cpu.mux('RD',['RD_R','RS'],'DestSel',4,1480,570)
# REG FILE two simultaneous combinational reads.
cpu.gate('AND','RF_WE',1,1690,690,'RegWrite','RUN')
cpu.sub('REGS12',1960,400,[('CLK',1),('RESET',1),('RF_WE',1),('RD',4),('WB',16),('RD',4),('RS',4)],[('A',16),('B',16),('R4',16)])
# ALU and flag register
cpu.mux('ALUB',['B','IMM16'],'ALUSrc',16,2020,710)
cpu.sub('ALU16',2410,700,[('A',16),('ALUB',16),('ALUOp',2)],[('ALUY',16),('ALUF',4)])
cpu.gate('AND','FLAG_WE',1,2230,940,'FlagWrite','RUN')
cpu.c(5,'Register',2450,900,width=4,label='ZNCV')
cpu.t('ALUF',4,2450,930);cpu.t('FLAG_WE',1,2450,950);cpu.t('CLK',1,2450,970);cpu.t('RESET',1,2480,990)
cpu.t('FLAGS',4,2510,930,'west')
cpu.split('FLAGS',4,[('Z_REG',1),('N_REG',1),('C_REG',1),('V_REG',1)],2600,950)
# Data RAM with debug access when RUN=0.  Addresses use entire 16-bit range and
# are rejected if >=16 by the SRAM's internal 12-bit high-address validation.
cpu.mux('RAM_ADDR',['DBG_ADDR','B'],'RUN',16,2490,1210)
cpu.mux('RAM_DIN',['DBG_DIN','A'],'RUN',16,2490,1300)
cpu.mux('RAM_WE_PRE',['DBG_WRITE','MemWrite'],'RUN',1,2490,1390)
cpu.inverter('RESET','NO_RESET',1,2550,1500)
cpu.gate('AND','RAM_WE',1,2690,1530,'RAM_WE_PRE','NO_RESET')
cpu.sub('RAM16_ASYNC',2810,1210,[('CLK',1),('RAM_ADDR',16),('RAM_DIN',16),('RAM_WE',1)],[('RAM_OUT',16),('RAM0',16)])
# Four choices for writing Rd: ALU, Rs, RAM data, or signed immediate.
cpu.mux('WB',['ALUY','B','RAM_OUT','IMM16'],'WBSel',16,2760,680)
# PC arithmetic; separate adders permit a single clock cycle.
cpu.const(1,16,1410,1540);cpu.t('ONE16',16,1410,1540,'west')
cpu.const(0,1,1410,1590);cpu.t('ZERO1',1,1410,1590,'west')
cpu.add('PC','ONE16','ZERO1','PC_SEQ','PC_C1',16,1790,1540)
cpu.add('PC','OFF16','ZERO1','PC_BR','PC_C2',16,1790,1690)
cpu.mux('NEXT_PC',['PC_SEQ','PC_BR'],'BranchTaken',16,2040,1620)

# Simple static consistency checks.
for c in [x for x in p if x.tag=='circuit']:
 nm=c.get('name')
 locs=[]; totals={}
 for t in c.findall('comp'):
  loc=t.get('loc');lib=t.get('lib');name=t.get('name')
  if lib=='0' and name=='Tunnel':
   label=next((a.get('val') for a in t.findall('a') if a.get('name')=='label'),None)
   ww=int(next((a.get('val') for a in t.findall('a') if a.get('name')=='width'),'1'))
   if label and label in totals and totals[label]!=ww:
    raise AssertionError(f'{nm} tunnel {label} widths mismatch {totals[label]} vs {ww}')
   totals[label]=ww
 for pin in c.findall('comp'):
  if pin.get('name') not in ('Pin','Tunnel') and pin.get('lib')=='0':pass
print('ROM:',[f'{w:04X}' for w in rom_words])
print('CONTROL ROM:',[f'{w:04X}' for w in rows])
# Write clean readable XML
s=minidom.parseString(ET.tostring(p,encoding='utf-8')).toprettyxml(indent='  ',encoding='utf-8')
out=O/'cpu16_harvard_prototipo.circ';out.write_bytes(s)
print('WROTE',out,'bytes=',len(s),'circuits=',[c.get('name') for c in p.findall('circuit')])