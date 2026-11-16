#include <cstdio>
#include <cstring>
int main() {
auto urus = "4.0 TT V8";
auto rsq8 = "4.0 TT V8";
puts(!strcmp(urus, rsq8)
  ? "engine SAME" : "DIFF");
}
