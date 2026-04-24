from camoufox.fingerprints import generate_context_fingerprint
preset = {
    'navigator': {},
    'screen': {},
    'webgl': {},
    'timezone': 'Asia/Ho_Chi_Minh',
}
fp = generate_context_fingerprint(preset=preset, webrtc_ip="1.1.1.1")
print(fp['context_options'])
