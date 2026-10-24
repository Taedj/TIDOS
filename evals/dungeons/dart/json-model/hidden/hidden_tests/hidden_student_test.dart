import 'dart:io';
import '../student.dart';

void expect(Object? actual, Object? expected, String label) {
  if (actual.toString() != expected.toString()) {
    stderr.writeln('FAIL $label: expected $expected, got $actual');
    exit(1);
  }
}

void main() {
  final s = Student.fromJson({'id': '42', 'name': 'Lina', 'birth': '2004-03-07T10:00:00', 'grades': [12, 13.5]});
  expect(s.id, 42, 'id from string');
  expect(s.birth, DateTime(2004, 3, 7, 10), 'birth');
  expect(s.grades, [12.0, 13.5], 'grades to double');
  final j = s.toJson();
  expect(j['birth'], '2004-03-07', 'birth date only');
  expect(j['grades'], [12.0, 13.5], 'grades json');
  expect(j['id'] is int, true, 'id int');
  final t = Student.fromJson({'id': 7, 'name': 'Omar'});
  expect(t.birth, null, 'missing birth');
  expect(t.grades.length, 0, 'missing grades');
  expect(t.toJson()['birth'], null, 'null birth json');
  final u = Student.fromJson({'id': 1, 'name': 'X', 'birth': null, 'grades': null});
  expect(u.grades.length, 0, 'null grades');
  final v = Student.fromJson({'id': 3, 'name': 'Y', 'birth': '0999-01-02', 'grades': [1]});
  expect(v.toJson()['birth'], '0999-01-02', 'zero padding');
  expect(Student.fromJson(s.toJson()).toJson(), s.toJson(), 'round trip');
  print('ok');
}
