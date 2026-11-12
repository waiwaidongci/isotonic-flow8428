import hashlib,json
VERSION='weighted-pava-lodo-v1'
def fingerprint(study,levels,readings,config):
 payload={'version':VERSION,'study':study,'levels':sorted(levels,key=lambda x:x['id']),'readings':sorted(readings,key=lambda x:x['specimen_ref']),'config':config}
 return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
