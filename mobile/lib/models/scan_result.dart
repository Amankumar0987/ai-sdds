/// scan_result.dart
/// =================
/// Mirrors core/detector.py's ScanResult.to_dict() exactly, so this
/// model and the Python API never drift apart silently.
library;

class Finding {
  final String type;
  final String label;
  final String maskedValue;
  final double confidence;
  final bool validated;
  final String severity;

  Finding({
    required this.type,
    required this.label,
    required this.maskedValue,
    required this.confidence,
    required this.validated,
    required this.severity,
  });

  factory Finding.fromJson(Map<String, dynamic> json) => Finding(
        type: json['type'] as String,
        label: json['label'] as String,
        maskedValue: json['masked_value'] as String,
        confidence: (json['confidence'] as num).toDouble(),
        validated: json['validated'] as bool,
        severity: json['severity'] as String,
      );
}

enum Verdict { block, warn, allow, rejected, degraded }

class ScanResult {
  final Verdict verdict;
  final List<Finding> findings;
  final String reason;
  final String mimeType;
  final int sizeBytes;
  final bool degraded; // true when this result came from a fail-open path (scanner unreachable)

  ScanResult({
    required this.verdict,
    required this.findings,
    required this.reason,
    required this.mimeType,
    required this.sizeBytes,
    this.degraded = false,
  });

  factory ScanResult.fromJson(Map<String, dynamic> json) {
    return ScanResult(
      verdict: _parseVerdict(json['verdict'] as String),
      findings: (json['findings'] as List<dynamic>? ?? [])
          .map((f) => Finding.fromJson(f as Map<String, dynamic>))
          .toList(),
      reason: json['reason'] as String? ?? '',
      mimeType: json['mime_type'] as String? ?? '',
      sizeBytes: json['size_bytes'] as int? ?? 0,
    );
  }

  /// Used on the fail-open path when the API itself could not be
  /// reached at all — mirrors background.js's scanFile() catch block.
  factory ScanResult.degradedAllow(String reason) => ScanResult(
        verdict: Verdict.allow,
        findings: const [],
        reason: reason,
        mimeType: '',
        sizeBytes: 0,
        degraded: true,
      );

  static Verdict _parseVerdict(String raw) {
    switch (raw) {
      case 'BLOCK':
        return Verdict.block;
      case 'WARN':
        return Verdict.warn;
      case 'REJECTED':
        return Verdict.rejected;
      default:
        return Verdict.allow;
    }
  }
}
