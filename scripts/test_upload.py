import urllib.request, json

file_path = r'c:\Users\krish\Downloads\sample_hyperspectral_crop_cube.npy'
with open(file_path, 'rb') as f:
    content = f.read()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
crlf = '\r\n'

part1 = f'--{boundary}{crlf}Content-Disposition: form-data; name="file"; filename="sample_hyperspectral_crop_cube.npy"{crlf}Content-Type: application/octet-stream{crlf}{crlf}'.encode('utf-8')
part2 = f'{crlf}--{boundary}{crlf}Content-Disposition: form-data; name="crop_type"{crlf}{crlf}Wheat (Triticum aestivum){crlf}--{boundary}--{crlf}'.encode('utf-8')

body_bytes = part1 + content + part2

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/hyperspectral/upload-and-analyze',
    data=body_bytes,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)

try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode('utf-8'))
    print('SUCCESS!')
    print('Analysis ID:', data.get('analysis_id'))
    print('Diagnosis:', data.get('diagnosis', {}).get('predicted_condition'))
    print('Confidence:', data.get('diagnosis', {}).get('confidence'))
    print('Stress:', data.get('early_stress', {}).get('composite_stress_score'))
except urllib.error.HTTPError as e:
    print('HTTP ERROR:', e.code, e.read().decode('utf-8'))
except Exception as e:
    print('ERROR:', e)

