/// api_client.dart
/// ================
/// Mirrors extension/background.js's scanFile() almost line-for-line:
/// same endpoint, same header, same FAIL-OPEN philosophy (a scanner
/// outage must allow the user to continue, never jam them forever —
/// but the caller must always be told via `ScanResult.degraded`).
library;

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../models/scan_result.dart';
import 'settings_store.dart';

class ApiClient {
  final SettingsStore _settingsStore;
  final http.Client _httpClient;

  ApiClient({SettingsStore? settingsStore, http.Client? httpClient})
      : _settingsStore = settingsStore ?? SettingsStore(),
        _httpClient = httpClient ?? http.Client();

  Future<ScanResult> scanFile(File file) async {
    final settings = await _settingsStore.load();

    if (!settings.enabled) {
      return ScanResult.degradedAllow('एक्सटेंशन अभी बंद है');
    }

    final uri = Uri.parse('${settings.apiBaseUrl}/v1/scan');
    final request = http.MultipartRequest('POST', uri)
      ..headers['X-API-Key'] = settings.apiKey
      ..files.add(await http.MultipartFile.fromPath('file', file.path));

    try {
      final streamedResponse =
          await _httpClient.send(request).timeout(const Duration(seconds: 20));
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode != 200) {
        return ScanResult.degradedAllow(
          'स्कैनर त्रुटि (HTTP ${response.statusCode}) - अस्थायी रूप से अनुमति दी गई',
        );
      }

      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      return ScanResult.fromJson(decoded);
    } catch (err) {
      // Fail-open: same philosophy as background.js — never let a
      // network hiccup permanently block the user from sharing a file.
      return ScanResult.degradedAllow('API से कनेक्ट नहीं हो सका: $err');
    }
  }
}
