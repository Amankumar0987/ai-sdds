/// main.dart
library;

import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const AiSddsApp());
}

class AiSddsApp extends StatelessWidget {
  const AiSddsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI-SDDS',
      theme: ThemeData(colorSchemeSeed: const Color(0xFF1F3864), useMaterial3: true),
      home: const HomeScreen(),
    );
  }
}
