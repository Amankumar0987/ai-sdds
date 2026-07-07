/// home_screen.dart
/// =================
/// Two entry points into the same scan flow:
///   1. Manual: user taps "फ़ाइल चुनें" / "फ़ोटो लें" inside this app.
///   2. Share-target: user is in ANY app (Gallery, ChatGPT app, etc),
///      taps "Share", picks "AI-SDDS से जाँचें" — Android delivers the
///      file to us via receive_sharing_intent. We scan it, and if
///      ALLOW/proceed, the share continues to whatever the user
///      originally meant to share to.
library;

import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';

import '../models/scan_result.dart';
import '../services/api_client.dart';
import '../widgets/verdict_card.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiClient _apiClient = ApiClient();
  final ImagePicker _imagePicker = ImagePicker();

  StreamSubscription? _shareIntentSub;
  ScanResult? _result;
  bool _scanning = false;

  @override
  void initState() {
    super.initState();
    _listenForSharedFiles();
  }

  void _listenForSharedFiles() {
    // Files shared into this app WHILE it's already running.
    _shareIntentSub = ReceiveSharingIntent.instance.getMediaStream().listen(
      (files) {
        if (files.isNotEmpty) _scanFile(File(files.first.path));
      },
      onError: (err) => debugPrint('share-intent stream error: $err'),
    );

    // Files shared into this app that LAUNCHED it (cold start).
    ReceiveSharingIntent.instance.getInitialMedia().then((files) {
      if (files.isNotEmpty) _scanFile(File(files.first.path));
    });
  }

  @override
  void dispose() {
    _shareIntentSub?.cancel();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['jpg', 'jpeg', 'png', 'pdf'],
    );
    if (result?.files.single.path != null) {
      _scanFile(File(result!.files.single.path!));
    }
  }

  Future<void> _takePhoto() async {
    final photo = await _imagePicker.pickImage(source: ImageSource.camera);
    if (photo != null) _scanFile(File(photo.path));
  }

  Future<void> _scanFile(File file) async {
    setState(() {
      _scanning = true;
      _result = null;
    });
    final result = await _apiClient.scanFile(file);
    setState(() {
      _scanning = false;
      _result = result;
    });
  }

  /// Called when the user taps "फिर भी जारी रखें" on a WARN result.
  /// In a real share-target flow this is where you'd hand the file
  /// back to the OS share sheet to continue to the originally-chosen
  /// app — that final hand-off uses platform-specific share APIs
  /// (e.g. `share_plus`) and is intentionally left as a clearly-marked
  /// follow-up rather than guessed at here without being able to test it.
  void _proceedAnyway() {
    setState(() {
      // Placeholder for the "continue share" hand-off — see comment above.
    });
  }

  void _cancel() {
    setState(() {
      _result = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI-SDDS'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            const Text(
              'किसी भी AI ऐप को फ़ाइल भेजने से पहले यहाँ जाँच लें — '
              'या किसी भी ऐप में "Share" दबाकर "AI-SDDS से जाँचें" चुनें।',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                ElevatedButton.icon(
                  onPressed: _scanning ? null : _pickFile,
                  icon: const Icon(Icons.file_open),
                  label: const Text('फ़ाइल चुनें'),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: _scanning ? null : _takePhoto,
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('फ़ोटो लें'),
                ),
              ],
            ),
            const SizedBox(height: 24),
            if (_scanning) const CircularProgressIndicator(),
            if (_result != null)
              VerdictCard(
                result: _result!,
                onProceedAnyway: _proceedAnyway,
                onCancel: _cancel,
              ),
          ],
        ),
      ),
    );
  }
}
