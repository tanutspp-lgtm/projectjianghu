WUXIA FLUTE ARENA v7.9M — Full Loading Gates (Web only)

1) Initial loading gate preloads/decodes 30 light character previews (~1.4MB total), with progress X/30. Opens character creator ONLY after all finish, so first click switches instantly even on fresh cache.
2) On entering offline or online world, a second fullscreen loading gate waits for the selected full 24-frame atlas plus all queued game world images (terrain, backgrounds, FX, legacy frames). World art fully loaded before rendering gameplay or initiating WebSocket connection.
3) Progress reports completed image files, not bytes transferred; it does not indicate network transfer percentage. Failed image displays retry.
4) IMPORTANT: Does not preload 30 full character sheets (~61MB) to avoid mobile download/memory overload. Online peers still lazy-load as they enter view, because they depend on who is connected.
5) Web-only change; server, physics, and art unchanged. No deployment.
