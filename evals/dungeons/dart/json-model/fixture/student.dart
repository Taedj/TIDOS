class Student {
  final int id;
  final String name;
  final DateTime? birth;
  final List<double> grades;

  Student(this.id, this.name, this.birth, this.grades);

  factory Student.fromJson(Map<String, dynamic> json) => Student(
      json['id'], json['name'], DateTime.parse(json['birth']), List<double>.from(json['grades']));

  Map<String, dynamic> toJson() =>
      {'id': id, 'name': name, 'birth': birth.toString(), 'grades': grades};
}
