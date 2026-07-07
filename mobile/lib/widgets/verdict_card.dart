/// verdict_card.dart
library;

import 'package:flutter/material.dart';
import '../models/scan_result.dart';

class VerdictCard extends StatelessWidget {
  final ScanResult result;
  final VoidCallback? onProceedAnyway;
  final VoidCallback? onCancel;

  const VerdictCard({
    super.key,
    required this.result,
    this.onProceedAnyway,
    this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    final (color, icon, title) = switch (result.verdict) {
      Verdict.block => (Colors.red.shade700, Icons.block, 'अपलोड ब्लॉक किया गया'),
      Verdict.warn => (Colors.orange.shade800, Icons.warning_amber, 'संभावित संवेदनशील जानकारी'),
      Verdict.rejected => (Colors.grey.shade700, Icons.error_outline, 'फ़ाइल अस्वीकृत'),
      Verdict.allow || Verdict.degraded => (Colors.green.shade700, Icons.verified, 'सुरक्षित'),
    };

    return Card(
      color: color.withValues(alpha: 0.08),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(title,
                      style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 16)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(result.reason),
            if (result.degraded) ...[
              const SizedBox(height: 8),
              Text(
                '⚠ स्कैनर अभी अनुपलब्ध था — यह फ़ाइल बिना जाँच के अनुमति दी गई',
                style: TextStyle(color: Colors.orange.shade900, fontSize: 12),
              ),
            ],
            if (result.findings.isNotEmpty) ...[
              const SizedBox(height: 12),
              ...result.findings.map(
                (f) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text('• ${f.label}: ${f.maskedValue} (${(f.confidence * 100).round()}%)',
                      style: const TextStyle(fontSize: 13)),
                ),
              ),
            ],
            if (result.verdict == Verdict.warn) ...[
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(onPressed: onCancel, child: const Text('रद्द करें')),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: onProceedAnyway,
                    child: const Text('फिर भी जारी रखें'),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
