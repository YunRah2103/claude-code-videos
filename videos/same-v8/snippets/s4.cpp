#include <cstdio>
struct Cover {};
struct Car {
  Cover cover() { return {}; }
  void fit(Cover) { puts("cover fits"); }
} urus, rsq8;
int main() {
// engine cover: reportedly
Cover c = urus.cover();
rsq8.fit(c);  // fits
}
