import 'dart:io';
import '../average.dart';

void expect(Object? actual, Object? expected, String label) {
  if (actual != expected) {
    stderr.writeln('FAIL $label: expected $expected, got $actual');
    exit(1);
  }
}

void main() {
  expect(average(null), 0.0, 'null');
  expect(average([]), 0.0, 'empty');
  expect(average([-1, -5]), 0.0, 'all absent');
  expect(average([10, 14]), 12.0, 'mean');
  expect(average([10, -1, 16]), 13.0, 'ignores absent');
  print('ok');
}
