from memory import UnsafePointer

struct Wrap:
    var p: UnsafePointer[Scalar[DType.uint8]]

fn main():
    print("Struct works")