/// settings_store.dart
/// ====================
/// Backed by flutter_secure_storage — Android Keystore / iOS Keychain.
/// This is a real security improvement over the browser extension's
/// chrome.storage.sync, which is NOT encrypted at rest the same way.
library;

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class Settings {
  final String apiBaseUrl;
  final String apiKey;
  final bool enabled;

  const Settings({
    required this.apiBaseUrl,
    required this.apiKey,
    required this.enabled,
  });

  static const defaults = Settings(
    apiBaseUrl: 'http://localhost:8000',
    apiKey: '',
    enabled: true,
  );

  Settings copyWith({String? apiBaseUrl, String? apiKey, bool? enabled}) =>
      Settings(
        apiBaseUrl: apiBaseUrl ?? this.apiBaseUrl,
        apiKey: apiKey ?? this.apiKey,
        enabled: enabled ?? this.enabled,
      );
}

class SettingsStore {
  static const _kApiBaseUrl = 'ai_sdds_api_base_url';
  static const _kApiKey = 'ai_sdds_api_key';
  static const _kEnabled = 'ai_sdds_enabled';

  final FlutterSecureStorage _storage;

  SettingsStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  Future<Settings> load() async {
    final apiBaseUrl = await _storage.read(key: _kApiBaseUrl) ?? Settings.defaults.apiBaseUrl;
    final apiKey = await _storage.read(key: _kApiKey) ?? Settings.defaults.apiKey;
    final enabledRaw = await _storage.read(key: _kEnabled);
    final enabled = enabledRaw == null ? Settings.defaults.enabled : enabledRaw == 'true';
    return Settings(apiBaseUrl: apiBaseUrl, apiKey: apiKey, enabled: enabled);
  }

  Future<void> save(Settings settings) async {
    await _storage.write(key: _kApiBaseUrl, value: settings.apiBaseUrl);
    await _storage.write(key: _kApiKey, value: settings.apiKey);
    await _storage.write(key: _kEnabled, value: settings.enabled.toString());
  }
}
