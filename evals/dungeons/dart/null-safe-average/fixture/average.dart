double average(List<int>? marks) {
  var sum = 0;
  for (final m in marks!) {
    sum += m;
  }
  return sum / marks.length;
}
