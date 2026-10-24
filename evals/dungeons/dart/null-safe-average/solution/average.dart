double average(List<int>? marks) {
  final present = (marks ?? const <int>[]).where((m) => m >= 0).toList();
  if (present.isEmpty) return 0.0;
  return present.reduce((a, b) => a + b) / present.length;
}
