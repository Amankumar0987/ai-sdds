/// settings_screen.dart
library;

import 'package:flutter/material.dart';
import '../services/settings_store.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final SettingsStore _store = SettingsStore();
  final _urlController = TextEditingController();
  final _keyController = TextEditingController();
  bool _enabled = true;
  bool _loading = true;
  String _status = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final settings = await _store.load();
    setState(() {
      _urlController.text = settings.apiBaseUrl;
      _keyController.text = settings.apiKey;
      _enabled = settings.enabled;
      _loading = false;
    });
  }

  Future<void> _save() async {
    await _store.save(Settings(
      apiBaseUrl: _urlController.text.trim().isEmpty
          ? Settings.defaults.apiBaseUrl
          : _urlController.text.trim(),
      apiKey: _keyController.text,
      enabled: _enabled,
    ));
    setState(() => _status = 'सेव हो गया');
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _status = '');
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(
      appBar: AppBar(title: const Text('AI-SDDS सेटिंग्स')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SwitchListTile(
              title: const Text('सुरक्षा सक्रिय करें'),
              value: _enabled,
              onChanged: (v) => setState(() => _enabled = v),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _urlController,
              decoration: const InputDecoration(
                labelText: 'API सर्वर पता',
                hintText: 'http://localhost:8000',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _keyController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'API Key',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 20),
            FilledButton(onPressed: _save, child: const Text('सेव करें')),
            const SizedBox(height: 8),
            Text(_status, style: const TextStyle(color: Colors.green)),
          ],
        ),
      ),
    );
  }
}
