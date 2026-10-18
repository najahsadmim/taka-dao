from __future__ import annotations
import json, os, threading, uuid, tempfile, mimetypes, io, zipfile, xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from flask import Flask, jsonify, request, send_file

ROOT = Path(__file__).resolve().parent
try:
 from dotenv import load_dotenv
 load_dotenv(ROOT / '.env')
except ImportError:
 pass
DATA = Path(os.getenv('TAKA_DAO_DATA_DIR', '/tmp/taka-dao/data' if os.getenv('VERCEL') else str(ROOT / 'data')))
LOCK = threading.RLock()
app = Flask(__name__)

@app.before_request
def cors_preflight():
 if request.method=='OPTIONS': return ('',204)

@app.after_request
def add_frontend_cors(response):
 origin=request.headers.get('Origin')
 allowed=os.getenv('FRONTEND_ORIGIN','https://taka-dao-frontend.vercel.app').rstrip('/')
 if allowed and origin and origin.rstrip('/')==allowed:
  response.headers['Access-Control-Allow-Origin']=allowed
  response.headers['Access-Control-Allow-Methods']='GET, POST, OPTIONS'
  response.headers['Access-Control-Allow-Headers']='Content-Type'
  response.headers['Vary']='Origin'
 return response
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'local-demo-change-me')
app.config['MAX_CONTENT_LENGTH'] = 11 * 1024 * 1024

SEED = {
 'settings': {'display_currency':'BDT','theme':'blue','daily_limit_mode':'manual','daily_limit':'1200','minimum_reserve':'10000','ai_provider':os.getenv('AI_PROVIDER','gemini')},
 'transactions': [
  {'id':'seed-t1','date':date.today().isoformat()+'T08:30:00','description':'Campus café','category':'Food','type':'expense','amount':'420','currency':'BDT','method':'Campus wallet','status':'successful','source':'demo','synthetic':True},
  {'id':'seed-t2','date':date.today().isoformat()+'T11:10:00','description':'Bus pass','category':'Transport','type':'expense','amount':'180','currency':'BDT','method':'Bank card (simulated)','status':'successful','source':'demo','synthetic':True},
  {'id':'seed-t3','date':(date.today()-timedelta(days=1)).isoformat()+'T13:00:00','description':'Groceries','category':'Groceries','type':'expense','amount':'950','currency':'BDT','method':'Cash','status':'successful','source':'demo','synthetic':True},
  {'id':'seed-t4','date':(date.today()-timedelta(days=3)).isoformat()+'T09:00:00','description':'Part-time wages','category':'Salary','type':'income','amount':'18500','currency':'BDT','method':'Bank transfer','status':'successful','source':'demo','synthetic':True}],
 'payment_events': [],
 'payment_methods': [{'id':'pm-card','name':'Bank card','detail':'•••• 2048','simulated':True,'enabled':True},{'id':'pm-wallet','name':'Digital wallet','detail':'Student wallet','simulated':True,'enabled':True},{'id':'pm-transfer','name':'Bank transfer','detail':'Demo transfer','simulated':True,'enabled':True}],
 'dues':[{'id':'due-1','name':'Tuition installment','category':'Education','amount':'42000','currency':'BDT','date':(date.today()+timedelta(days=12)).isoformat(),'priority':'essential','status':'upcoming','confirmed':True},{'id':'due-2','name':'Rent','category':'Housing','amount':'18000','currency':'BDT','date':(date.today()+timedelta(days=5)).isoformat(),'priority':'essential','status':'upcoming','confirmed':True},{'id':'due-3','name':'Insurance premium','category':'Insurance','amount':'3200','currency':'BDT','date':(date.today()+timedelta(days=21)).isoformat(),'priority':'important','status':'upcoming','confirmed':False}],
 'funds':[{'id':'fund-1','source':'Family support','amount':'25000','currency':'BDT','date':(date.today()+timedelta(days=4)).isoformat(),'confidence':'medium','status':'expected','synthetic':True}],
 'budgets':[{'id':'b1','category':'Food','amount':'12000','currency':'BDT'},{'id':'b2','category':'Transport','amount':'4500','currency':'BDT'},{'id':'b3','category':'Education','amount':'50000','currency':'BDT'},{'id':'b4','category':'Housing','amount':'20000','currency':'BDT'}],
 'notifications':[{'id':'n1','message':'Welcome! Demo records are marked synthetic.','date':datetime.now().isoformat(),'read':False}],
 'insurance':[], 'tax_records':[], 'autopay_rules':[], 'priorities':[], 'allocations':[], 'audit_logs':[]
}

def init_store():
 DATA.mkdir(exist_ok=True)
 for key, value in SEED.items():
  p=DATA/f'{key}.json'
  if not p.exists(): atomic_write(p,value)

def atomic_write(path, value):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)

def read(key):
 with LOCK:
  p=DATA/f'{key}.json'
  if not p.exists(): return []
  try: return json.loads(p.read_text(encoding='utf-8'))
  except (json.JSONDecodeError,OSError) as e: raise ValueError(f'{key} data is unavailable because its JSON file is invalid; existing file was preserved.') from e

def write(key, value):
 with LOCK: atomic_write(DATA/f'{key}.json',value)

def money(v):
 try:
  d=Decimal(str(v))
  if not d.is_finite() or d < 0: raise ValueError()
  return d
 except (InvalidOperation,ValueError,TypeError): raise ValueError('Enter a valid non-negative amount.')

def fmt(d): return format(d.quantize(Decimal('0.01')), 'f').rstrip('0').rstrip('.') or '0'
def record_id(): return str(uuid.uuid4())
def event(message,extra=None):
 rows=read('notifications'); rows.insert(0,{'id':record_id(),'message':message,'date':datetime.now().isoformat(),'read':False,**(extra or {})}); write('notifications',rows[:100])

def allocate_income(tx):
 amount=money(tx['amount']); currency=tx['currency']; dues=read('dues'); priorities=read('priorities')
 if not priorities or not priorities[0].get('items'): return []
 prior_balance=sum((money(t['amount']) if t.get('type') in ('income','refund') else -money(t['amount']) for t in read('transactions') if t.get('id')!=tx['id'] and t.get('status')=='successful' and t.get('currency')==currency),Decimal(0))
 open_due=sum((max(Decimal(0),money(d.get('amount','0'))-money(d.get('allocated_amount','0'))) for d in dues if d.get('status') not in ('paid','cancelled') and d.get('currency')==currency),Decimal(0))
 if prior_balance>=open_due: return []
 names=[x.strip().casefold() for x in str(priorities[0]['items']).split(',') if x.strip()]
 allocs=read('allocations'); new=[]
 for name in names:
  for due in dues:
   if due.get('status') in ('paid','cancelled') or due.get('currency')!=currency or not (name in due.get('name','').casefold() or name==due.get('category','').casefold()): continue
   outstanding=max(Decimal(0),money(due.get('amount','0'))-money(due.get('allocated_amount','0')))
   if outstanding<=0 or amount < outstanding*Decimal('0.5'): continue
   part=min(amount,outstanding); due['allocated_amount']=fmt(money(due.get('allocated_amount','0'))+part); amount-=part
   row={'id':record_id(),'income_id':tx['id'],'due_id':due['id'],'due_name':due['name'],'amount':fmt(part),'currency':currency,'created_at':datetime.now().isoformat()}
   allocs.insert(0,row); new.append(row); event(f"{currency} {fmt(part)} allocated to {due['name']}.",{'allocation_id':row['id'],'allocation_due_id':due['id'],'allocation_amount':fmt(part),'allocation_currency':currency,'allocation_name':due['name']})
   if amount<=0: break
  if amount<=0: break
 # Any remainder can go to other open obligations after the explicit priority items.
 if amount>0:
  for due in sorted(dues,key=lambda x:(0 if any(w in str(x.get('name','')).casefold() for w in ('friend','debt','loan')) else 1,str(x.get('date','')))):
   if due.get('status') in ('paid','cancelled') or due.get('currency')!=currency or due.get('name','').casefold() in names or due.get('category','').casefold() in names: continue
   outstanding=max(Decimal(0),money(due.get('amount','0'))-money(due.get('allocated_amount','0')))
   if outstanding<=0 or amount < outstanding*Decimal('0.5'): continue
   part=min(amount,outstanding); due['allocated_amount']=fmt(money(due.get('allocated_amount','0'))+part); amount-=part
   row={'id':record_id(),'income_id':tx['id'],'due_id':due['id'],'due_name':due['name'],'amount':fmt(part),'currency':currency,'created_at':datetime.now().isoformat()}
   allocs.insert(0,row); new.append(row); event(f"{currency} {fmt(part)} allocated to {due['name']}.",{'allocation_id':row['id'],'allocation_due_id':due['id'],'allocation_amount':fmt(part),'allocation_currency':currency,'allocation_name':due['name']})
   if amount<=0: break
 if new: write('dues',dues); write('allocations',allocs)
 return new

def dashboard():
 tx=read('transactions'); settings=read('settings'); settings=settings if isinstance(settings,dict) else SEED['settings']
 currency=settings.get('display_currency','BDT'); today=date.today().isoformat()
 expenses=[x for x in tx if x.get('status')=='successful' and x.get('type')=='expense' and x.get('currency')==currency]
 todays=[x for x in expenses if str(x.get('date',''))[:10]==today]
 total=sum((money(x['amount']) for x in todays),Decimal(0)); limit=money(settings.get('daily_limit','0'))
 cats={}
 for x in todays: cats[x.get('category','Other')]=cats.get(x.get('category','Other'),Decimal(0))+money(x['amount'])
 dues=[d for d in read('dues') if d.get('status') not in ('paid','cancelled') and d.get('currency')==currency]
 funds=[f for f in read('funds') if f.get('status') in ('expected','confirmed','delayed') and f.get('currency')==currency]
 month_exp=sum((money(x['amount']) for x in expenses if str(x.get('date',''))[:7]==today[:7]),Decimal(0))
 balance=sum((money(x['amount']) if x.get('type') in ('income','refund') else -money(x['amount']) for x in tx if x.get('status')=='successful' and x.get('currency')==currency),Decimal(0))
 due_sum=sum((money(d['amount']) for d in dues),Decimal(0))
 if settings.get('daily_limit_mode')=='automatic':
  # Forecast considers obligations and reserves; expected transfers are excluded from available cash.
  days=max(1,(date.today().replace(day=1)+timedelta(days=32)).replace(day=1).__sub__(date.today()).days)
  limit=max(Decimal(0),(balance-due_sum-money(settings.get('minimum_reserve','0')))/days)
 safe={'spent':fmt(total),'limit':fmt(limit),'remaining':fmt(max(Decimal(0),limit-total)),'over':fmt(max(Decimal(0),total-limit)),'excess_percent':fmt((total-limit)*100/limit) if limit>0 and total>limit else None,'within':total<=limit,'configured':limit>0,'mode':settings.get('daily_limit_mode','manual'),'categories':[{'name':k,'amount':fmt(v),'share':float(v*100/total) if total else 0} for k,v in sorted(cats.items(),key=lambda x:x[1],reverse=True)]}
 return {'currency':currency,'safe':safe,'transactions':tx,'dues':dues,'funds':funds,'budgets':read('budgets'),'notifications':read('notifications'),'payment_methods':read('payment_methods'),'settings':settings,'allocations':read('allocations'),'autopay_rules':read('autopay_rules'),'summary':{'balance':fmt(balance),'month_expenses':fmt(month_exp),'due_total':fmt(due_sum),'expected_total':fmt(sum((money(f['amount']) for f in funds),Decimal(0))),'due_count':len(dues),'transaction_count':len(tx)}}

CATEGORY_LABELS={'passport_bio':'Passport bio page','profile_photo':'Profile picture','enrollment_verification':'Enrollment verification','transcript':'Academic transcript','degree_certificate':'Degree certificate','student_visa':'Student visa','admission_letter':'Admission letter','insurance_policy':'Insurance policy','medical_record':'Medical record','medical_bill':'Medical bill','other_academic':'Other academic document'}
PRIVATE=Path(os.getenv('TAKA_DAO_PRIVATE_DIR', '/tmp/taka-dao/private_documents' if os.getenv('VERCEL') else str(ROOT/'private_documents')))
KEY_FILE=Path(os.getenv('TAKA_DAO_KEY_FILE', '/tmp/taka-dao/.instance/document.key' if os.getenv('VERCEL') else str(ROOT/'.instance'/'document.key')))
def document_cipher():
 from cryptography.fernet import Fernet
 env=os.getenv('DOCUMENT_ENCRYPTION_KEY')
 if env: key=env.encode('ascii')
 else:
  KEY_FILE.parent.mkdir(parents=True,exist_ok=True)
  if not KEY_FILE.exists():
   tmp=KEY_FILE.with_suffix('.tmp'); tmp.write_bytes(Fernet.generate_key())
   try: os.chmod(tmp,0o600)
   except OSError: pass
   try: os.replace(tmp,KEY_FILE)
   except FileExistsError: tmp.unlink(missing_ok=True)
  key=KEY_FILE.read_bytes().strip()
 return Fernet(key)
def accepted_upload(category, filename, data):
 ext=Path(filename).suffix.lower()
 if category in ('profile_photo','passport_bio','medical_record','medical_bill'):
  allowed={'.jpg','.jpeg','.png','.webp'}
 else: allowed={'.pdf','.jpg','.jpeg','.png','.webp','.docx'}
 if ext not in allowed: raise ValueError('Choose a supported file type for this document.')
 valid=(ext=='.pdf' and data.startswith(b'%PDF-')) or (ext in ('.jpg','.jpeg') and data.startswith(b'\xff\xd8\xff')) or (ext=='.png' and data.startswith(b'\x89PNG\r\n\x1a\n')) or (ext=='.webp' and len(data)>12 and data[:4]==b'RIFF' and data[8:12]==b'WEBP') or (ext=='.docx' and data.startswith(b'PK\x03\x04'))
 if not valid: raise ValueError('The file contents do not match the selected file type.')
 return mimetypes.guess_type('file'+ext)[0] or 'application/octet-stream'

@app.get('/')
def home(): return jsonify(name='Taka Dao API', status='online', message='Connect the frontend using TAKA_DAO_API_BASE.')
@app.get('/api/documents')
def list_documents():
 return jsonify([{k:v for k,v in row.items() if k not in ('storage_name','mime_type')} for row in read('documents') if row.get('category')!='profile_photo'])
@app.post('/api/documents')
def upload_document():
 f=request.files.get('file'); category=str(request.form.get('category',''))
 try:
  if not f or not f.filename: raise ValueError('Choose a file to upload.')
  if category not in CATEGORY_LABELS: raise ValueError('Choose a supported document type.')
  raw=f.stream.read(10*1024*1024+1)
  if not raw: raise ValueError('The selected file is empty.')
  if len(raw)>10*1024*1024: raise ValueError('Files must be 10 MB or smaller.')
  if category=='profile_photo' and len(raw)>5*1024*1024: raise ValueError('Profile pictures must be 5 MB or smaller.')
  mime=accepted_upload(category,f.filename,raw)
  PRIVATE.mkdir(parents=True,exist_ok=True)
  doc_id=record_id(); stored=doc_id+'.enc'; encrypted=document_cipher().encrypt(raw)
  path=PRIVATE/stored
  with LOCK: path.write_bytes(encrypted)
  try: os.chmod(path,0o600)
  except OSError: pass
  row={'id':doc_id,'category':category,'category_label':CATEGORY_LABELS[category],'filename':Path(f.filename).name[:160],'created_at':datetime.now().isoformat(),'storage_name':stored,'mime_type':mime}
  with LOCK:
   rows=read('documents'); rows.insert(0,row); write('documents',rows)
  return jsonify({k:v for k,v in row.items() if k not in ('storage_name','mime_type')}),201
 except ValueError as e: return jsonify(error=str(e)),400
 except Exception as e:
  app.logger.exception('Document upload failed')
  return jsonify(error='Upload could not be completed. Check that local encryption is available.'),500
@app.get('/api/documents/<doc_id>/content')
def document_content(doc_id):
 row=next((x for x in read('documents') if x.get('id')==doc_id),None)
 if not row:return jsonify(error='Document not found'),404
 try:
  data=document_cipher().decrypt((PRIVATE/row['storage_name']).read_bytes())
  return send_file(io.BytesIO(data),mimetype=row.get('mime_type','application/octet-stream'),download_name=row.get('filename','document'),as_attachment=False,conditional=False)
 except Exception:
  app.logger.exception('Document could not be decrypted')
  return jsonify(error='Document is unavailable.'),500

def document_text(row, cfg):
 cache=PRIVATE/(row['id']+'.text.enc')
 try:
  if cache.exists(): return document_cipher().decrypt(cache.read_bytes()).decode('utf-8')[:12000]
 except Exception: pass
 data=document_cipher().decrypt((PRIVATE/row['storage_name']).read_bytes()); ext=Path(row.get('filename','')).suffix.lower(); text=''
 if ext=='.pdf':
  from pypdf import PdfReader
  pages=PdfReader(io.BytesIO(data)).pages; parts=[]; needs_ocr=[]
  for i,page in enumerate(pages):
   page_text=(page.extract_text() or '').strip()
   if len(page_text)>=30: parts.append(page_text)
   else: needs_ocr.append(i)
  if needs_ocr:
   try:
    import fitz
    with fitz.open(stream=data,filetype='pdf') as pdf:
     for i in needs_ocr[:12]:
      pix=pdf[i].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
      parts.append(ollama_ocr(pix.tobytes('png'),cfg))
   except Exception as e:
    raise RuntimeError('Scanned PDF OCR needs PyMuPDF and a vision-capable Ollama model.') from e
  text='\n'.join(x for x in parts if x.strip())[:12000]
 elif ext=='.docx':
  with zipfile.ZipFile(io.BytesIO(data)) as z: root=ET.fromstring(z.read('word/document.xml'))
  text=' '.join(t.text or '' for t in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))[:12000]
 elif ext in ('.jpg','.jpeg','.png','.webp'): text=ollama_ocr(data,cfg)[:12000]
 elif ext in ('.txt','.md'): text=data.decode('utf-8','ignore')[:12000]
 if text.strip():
  try:
   encrypted=document_cipher().encrypt(text.encode('utf-8')); cache.write_bytes(encrypted)
   try: os.chmod(cache,0o600)
   except OSError: pass
  except Exception: app.logger.warning('Could not cache extracted document text.')
 return text

def ollama_ocr(image_bytes, cfg):
 from ollama import Client
 headers={'Authorization':'Bearer '+cfg['api_key']} if cfg['api_key'] else None
 client=Client(host=cfg['host'],headers=headers)
 result=client.chat(model=cfg['model'],messages=[{'role':'user','content':'Transcribe the legible text in this document image exactly. Preserve amounts, dates, policy terms, headings, and table labels. Do not summarize, infer, or answer questions. Mark unreadable words as [unclear].','images':[image_bytes]}],stream=False)
 transcription=result.message.content
 if not isinstance(transcription,str) or not transcription.strip(): raise RuntimeError('OCR returned no text.')
 return transcription.strip()

@app.get('/api/dashboard')
def api_dashboard():
 try:return jsonify(dashboard())
 except ValueError as e:return jsonify(error=str(e)),422
@app.get('/api/<key>')
def list_records(key):
 if key not in ('transactions','dues','funds','budgets','payment_methods','payment_events','notifications','insurance','tax_records','autopay_rules','priorities'): return jsonify(error='Unknown collection'),404
 try:return jsonify(read(key))
 except ValueError as e:return jsonify(error=str(e)),422
@app.post('/api/transactions')
def add_transaction():
 data=request.get_json(silent=True) or {}
 try:
  amount=money(data.get('amount')); currency=str(data.get('currency','')).upper(); desc=str(data.get('description','')).strip()
  if not desc or len(desc)>120 or len(currency)!=3: raise ValueError('Description and three-letter currency are required.')
  if data.get('type') not in ('expense','income','refund','transfer'): raise ValueError('Choose a supported transaction type.')
  row={'id':record_id(),'date':data.get('date') or datetime.now().isoformat(),'description':desc,'category':str(data.get('category','Other'))[:48],'type':data['type'],'amount':fmt(amount),'currency':currency,'method':str(data.get('method','Manual'))[:48],'status':'successful','source':'manual','synthetic':False}
  rows=read('transactions'); rows.insert(0,row); write('transactions',rows); event('Transaction recorded: '+desc)
  if row['type']=='income': allocate_income(row)
  return jsonify(row),201
 except ValueError as e:return jsonify(error=str(e)),400
@app.post('/api/payments')
def payment():
 data=request.get_json(silent=True) or {}; idem=str(data.get('idempotency_key') or '')
 try:
  if not idem: raise ValueError('Payment reference is required.')
  events=read('payment_events')
  old=next((x for x in events if x.get('idempotency_key')==idem),None)
  if old: return jsonify(old),200
  amount=money(data.get('amount')); currency=str(data.get('currency','')).upper(); desc=str(data.get('description','')).strip(); recipient=str(data.get('recipient','')).strip()
  methods=read('payment_methods'); method=next((x for x in methods if x['id']==data.get('method_id') and x.get('enabled')),None)
  if not method: raise ValueError('Select an enabled simulated payment method.')
  if not desc or not recipient or len(currency)!=3: raise ValueError('Recipient, description and three-letter currency are required.')
  allocation_id=str(data.get('allocation_id') or '')
  allocs=read('allocations'); allocation=next((x for x in allocs if x.get('id')==allocation_id and x.get('status')!='paid'),None) if allocation_id else None
  if allocation_id and (not allocation or allocation.get('currency')!=currency): raise ValueError('The selected allocation is no longer available.')
  success=data.get('outcome','success')=='success'; eventrow={'id':record_id(),'idempotency_key':idem,'date':datetime.now().isoformat(),'recipient':recipient,'description':desc,'amount':fmt(amount),'currency':currency,'method':method['name'],'status':'successful' if success else 'failed','simulated':True}
  if success:
   tx={'id':record_id(),'event_id':eventrow['id'],'date':eventrow['date'],'description':desc,'category':str(data.get('category','Other')),'type':'expense','amount':fmt(amount),'currency':currency,'method':method['name'],'status':'successful','source':'simulated_payment','synthetic':False}
   eventrow['transaction_id']=tx['id']; rows=read('transactions'); rows.insert(0,tx); write('transactions',rows)
   if allocation:
    dues=read('dues'); due=next((x for x in dues if x.get('id')==allocation.get('due_id')),None)
    if due:
     paid=money(allocation['amount']); remaining=max(Decimal(0),money(due.get('amount','0'))-paid)
     due['amount']=fmt(remaining); due['allocated_amount']=fmt(max(Decimal(0),money(due.get('allocated_amount','0'))-paid))
     if remaining==0: due['status']='paid'
     allocation['status']='paid'; allocation['paid_transaction_id']=tx['id']; write('dues',dues); write('allocations',allocs)
     eventrow['allocation_id']=allocation_id; eventrow['allocation_paid']=fmt(paid)
   event(f"Simulated payment successful: {currency} {fmt(amount)} to {recipient}.")
  else: event(f"Simulated payment failed: {currency} {fmt(amount)} to {recipient}. No expense recorded.")
  events.insert(0,eventrow); write('payment_events',events); return jsonify(eventrow),201
 except ValueError as e:return jsonify(error=str(e)),400
@app.post('/api/<key>')
def add_record(key):
 allowed={'dues','funds','budgets','insurance','tax_records','autopay_rules','priorities'}
 if key not in allowed:return jsonify(error='Unknown collection'),404
 data=request.get_json(silent=True) or {}
 try:
  name=str(data.get('name') or data.get('source') or data.get('category') or '').strip()
  amount=money(data.get('amount'))
  if not name: raise ValueError('A name is required.')
  curr=str(data.get('currency','')).upper()
  if len(curr)!=3: raise ValueError('Currency must be a three-letter code.')
  row={'id':record_id(),**data,'amount':fmt(amount),'currency':curr}; rows=read(key); rows.insert(0,row); write(key,rows); event(f'{key.rstrip("s").title()} added: {name}.')
  if key=='autopay_rules':
   row.update(calendar_kind='due',date=data.get('start_date'),calendar_day=data.get('day_of_month'),status='scheduled')
   rules=read(key); rules[0]=row; write(key,rules)
   event(f"Autopay scheduled: {name} is due {data.get('start_date')}.")
  return jsonify(row),201
 except ValueError as e:return jsonify(error=str(e)),400

@app.post('/api/allocations/<allocation_id>/reallocate')
def reallocate(allocation_id):
 data=request.get_json(silent=True) or {}; allocs=read('allocations'); row=next((x for x in allocs if x.get('id')==allocation_id),None)
 if not row:return jsonify(error='Allocation not found.'),404
 dues=read('dues'); old=next((x for x in dues if x.get('id')==row.get('due_id')),None); new=next((x for x in dues if x.get('id')==data.get('due_id')),None)
 if not new or new.get('status') in ('paid','cancelled') or new.get('currency')!=row.get('currency'):return jsonify(error='Choose an open obligation in the same currency.'),400
 if old:old['allocated_amount']=fmt(max(Decimal(0),money(old.get('allocated_amount','0'))-money(row['amount'])))
 new['allocated_amount']=fmt(money(new.get('allocated_amount','0'))+money(row['amount'])); row['due_id']=new['id']; row['due_name']=new['name']; row['reallocated_at']=datetime.now().isoformat(); write('dues',dues); write('allocations',allocs)
 notes=read('notifications')
 for note in notes:
  if note.get('allocation_id')==allocation_id: note.update(allocation_due_id=new['id'],allocation_name=new['name'])
 write('notifications',notes); event(f"{row['currency']} {row['amount']} reallocated to {new['name']}."); return jsonify(row)
@app.patch('/api/settings')
def settings():
 data=request.get_json(silent=True) or {}; current=read('settings'); current=current if isinstance(current,dict) else {}
 try:
  if 'daily_limit' in data: data['daily_limit']=fmt(money(data['daily_limit']))
  if 'minimum_reserve' in data: data['minimum_reserve']=fmt(money(data['minimum_reserve']))
  if data.get('daily_limit_mode') not in (None,'manual','automatic'): raise ValueError('Invalid limit mode.')
  if data.get('display_currency') and len(data['display_currency'])!=3: raise ValueError('Currency must be a three-letter code.')
  current.update(data); write('settings',current); return jsonify(current)
 except ValueError as e:return jsonify(error=str(e)),400
def ollama_configuration():
 provider=os.getenv('AI_PROVIDER','').strip().lower()
 model=os.getenv('OLLAMA_MODEL','').strip()
 host=os.getenv('OLLAMA_BASE_URL','http://127.0.0.1:11434').strip().rstrip('/')
 if host.endswith('/api'): host=host[:-4]
 key=os.getenv('OLLAMA_API_KEY','').strip()
 cloud=host.startswith('https://ollama.com')
 configured=(provider=='ollama' and bool(model) and bool(host) and (not cloud or bool(key)))
 try:
  import importlib.util
  sdk=importlib.util.find_spec('ollama') is not None
 except (ImportError,ValueError): sdk=False
 return {'provider':provider or 'not configured','model':model,'host':host,'api_key':key,'cloud':cloud,'configured':configured,'sdk_available':sdk}

@app.get('/api/assistant/status')
def assistant_status():
 cfg=ollama_configuration()
 return jsonify(provider=cfg['provider'],model=cfg['model'],available=cfg['configured'] and cfg['sdk_available'])

@app.post('/api/chat')
def assistant_chat():
 cfg=ollama_configuration()
 if not cfg['configured']:
  return jsonify(error='Configure AI_PROVIDER=ollama, OLLAMA_BASE_URL and OLLAMA_MODEL in .env; Ollama Cloud also requires OLLAMA_API_KEY.'),503
 if not cfg['sdk_available']:
  return jsonify(error='Ollama client is missing. Install the project requirements, then restart the app.'),503
 data=request.get_json(silent=True) or {}; incoming=data.get('messages')
 if not isinstance(incoming,list) or not incoming:
  return jsonify(error='Send at least one message.'),400
 if len(incoming)>20:return jsonify(error='Keep each conversation to 20 messages or fewer.'),400
 messages=[{'role':'system','content':'You are Taka Dao’s student tax and insurance guide. Use supplied document context and general education; distinguish the two and cite the document filename. Say when information is missing. Never diagnose or promise coverage/claim approval. For urgent injury advise emergency care. Recommend checking current official rules. Never ask for secrets.'}]
 if data.get('use_documents') is True:
  settings=read('settings'); country=settings.get('profile_residence') or settings.get('tax_jurisdiction') or 'not specified'; topic=str(data.get('topic','tax')).lower(); snippets=[]; unreadable=[]
  for row in read('documents'):
   category=row.get('category','')
   if category in ('profile_photo','passport_bio'): continue
   if topic=='insurance' and category not in ('insurance_policy','medical_record','medical_bill','other_academic'): continue
   if topic=='tax' and category in ('insurance_policy','medical_record','medical_bill'): continue
   try: content=document_text(row,cfg)
   except Exception:
    app.logger.warning('Could not extract/OCR uploaded document %s.',row.get('id'))
    unreadable.append(row.get('filename','uploaded document')); continue
   if content.strip(): snippets.append(f"Document: {row.get('filename')} ({row.get('category_label')})\n{content}")
  context='\n\n'.join(snippets)[:18000]
  if unreadable: context+=f"\n\nOCR could not read: {', '.join(unreadable)}. Tell the user these files could not be read and may require a vision-capable Ollama model or a searchable PDF."
  if not context.strip(): context='No uploaded document contained readable text. Scanned PDFs and document images will be OCR-processed by the configured vision-capable Ollama model.'
  messages.append({'role':'system','content':f"User opted in to share private document text for this request. Country/jurisdiction: {country}. Use only relevant excerpts and avoid repeating personal identifiers.\n{context}"})
 for item in incoming:
  if not isinstance(item,dict) or item.get('role') not in ('user','assistant') or not isinstance(item.get('content'),str):
   return jsonify(error='Messages must have a user or assistant role and text content.'),400
  content=item['content'].strip()
  if not content or len(content)>4000:return jsonify(error='Each message must contain 1–4,000 characters.'),400
  messages.append({'role':item['role'],'content':content})
 try:
  from ollama import Client
  headers={'Authorization':'Bearer '+cfg['api_key']} if cfg['api_key'] else None
  client=Client(host=cfg['host'],headers=headers)
  result=client.chat(model=cfg['model'],messages=messages,stream=False)
  answer=result.message.content
  if not isinstance(answer,str) or not answer.strip():raise RuntimeError('empty model response')
  return jsonify(reply=answer.strip(),model=cfg['model'])
 except Exception as exc:
  app.logger.warning('Ollama chat request failed (%s).',type(exc).__name__)
  return jsonify(error='Ollama could not complete the reply. Check the Ollama server, model name, and Cloud API key.'),502

@app.post('/api/reset-demo')
def reset_demo():
 with LOCK:
  for key,value in SEED.items(): atomic_write(DATA/f'{key}.json',value)
 return jsonify(ok=True)

init_store()
if __name__=='__main__': app.run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)

