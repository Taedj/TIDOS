class Student {
  final int id;
  final String name;
  final DateTime? birth;
  final List<double> grades;

  Student(this.id, this.name, this.birth, this.grades);

  factory Student.fromJson(Map<String, dynamic> json) {
    final rawId = json['id'];
    final id = rawId is int ? rawId : int.parse(rawId.toString());
    final rawBirth = json['birth'];
    final birth = rawBirth == null ? null : DateTime.parse(rawBirth as String);
    final grades = ((json['grades'] as List?) ?? const []).map((g) => (g as num).toDouble()).toList();
    return Student(id, json['name'] as String, birth, grades);
  }

  Map<String, dynamic> toJson() {
    final b = birth;
    String two(int v) => v.toString().padLeft(2, '0');
    return {
      'id': id,
      'name': name,
      'birth': b == null ? null : '${b.year.toString().padLeft(4, '0')}-${two(b.month)}-${two(b.day)}',
      'grades': grades.map((g) => g.toDouble()).toList(),
    };
  }
}
