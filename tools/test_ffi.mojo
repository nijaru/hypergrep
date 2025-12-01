from memory import UnsafePointer, alloc

fn main():
    # Test the new alloc syntax found in stdlib tests
    var ptr = alloc[UInt8](64)
    print("Allocated 64 bytes successfully!")
    
    # Test pointer arithmetic/access
    ptr[0] = 10
    if ptr[0] == 10:
        print("Read/Write verified.")
        
    ptr.free()
    print("Freed.")
