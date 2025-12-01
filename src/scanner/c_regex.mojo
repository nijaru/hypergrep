from sys import external_call
from memory import UnsafePointer, alloc, AddressSpace
# Try importing the alias directly if possible, or re-defining it if it's public
# alloc returns this type, so it must be accessible or nameable?
# Actually, check if 'ExternalMutPointer' is exported from 'memory'.
# If not, we might be able to rely on 'auto' (var) but not for struct fields.

# Let's try 'UnsafePointer' one more time with what we learned about ExternalMutPointer.
# ExternalMutPointer is an alias for ExternalPointer with mut=True.
# ExternalPointer aliases UnsafePointer?

# Let's try creating our OWN alias that mimics ExternalMutPointer.
# alias MyPtr[T: AnyType] = UnsafePointer[T, mut=True] -> This failed "out of order".

# What if we import 'ExternalMutPointer' from 'memory.unsafe_pointer'?
from memory.unsafe_pointer import ExternalMutPointer

alias REG_EXTENDED = 1
alias REG_ICASE    = 2
alias REG_NOSUB    = 4
alias REG_NEWLINE  = 8
alias REGEX_T_SIZE = 128
alias CInt = Int32

alias VoidPtr = ExternalMutPointer[Scalar[DType.uint8]]
# For ConstCharPtr, we might need ExternalPointer with mut=False?
# Or just UnsafePointer?
# Let's use VoidPtr (Mutable) for everything for now, C doesn't care about Mojo constness (it casts void*).

fn regcomp(preg: VoidPtr, pattern: VoidPtr, cflags: CInt) -> CInt:
    return external_call["regcomp", CInt](preg, pattern, cflags)

fn regexec(preg: VoidPtr, string: VoidPtr, nmatch: Int, pmatch: VoidPtr, eflags: CInt) -> CInt:
    return external_call["regexec", CInt](preg, string, nmatch, pmatch, eflags)

fn regfree(preg: VoidPtr):
    external_call["regfree", NoneType](preg)

struct Regex:
    var _preg: VoidPtr
    var _pattern: String
    var _initialized: Bool

    fn __init__(out self, pattern: String):
        self._preg = alloc[Scalar[DType.uint8]](REGEX_T_SIZE)
        self._pattern = pattern
        self._initialized = False
        
        var p_copy = pattern
        # unsafe_cstr_ptr returns ...?
        # We cast to VoidPtr (Mutable)
        var c_pattern = p_copy.unsafe_cstr_ptr().bitcast[Scalar[DType.uint8]]().unsafe_mut_cast[True]()
        # unsafe_mut_cast[True] returns UnsafePointer(mut=True). 
        # Does it return ExternalMutPointer? 
        # If ExternalMutPointer is alias for UnsafePointer(mut=True), yes.
        
        var ret = regcomp(self._preg, c_pattern, CInt(REG_EXTENDED | REG_NOSUB | REG_ICASE))
        if ret == 0:
            self._initialized = True
        else:
            print("Regex compilation failed for: " + pattern)

    # Fix 'owned' warning by removing it (implicit) or using 'deinit'.
    # Let's try 'owned' again just to get past the import error first.
    fn __moveinit__(out self, owned existing: Self):
        self._preg = existing._preg
        self._pattern = existing._pattern
        self._initialized = existing._initialized
        existing._initialized = False

    fn __del__(owned self):
        if self._initialized:
            regfree(self._preg)
            self._preg.free()

    fn matches(self, text: String) -> Bool:
        if not self._initialized:
            return False
            
        var t_copy = text
        var c_text = t_copy.unsafe_cstr_ptr().bitcast[Scalar[DType.uint8]]().unsafe_mut_cast[True]()
        
        var dummy = alloc[Scalar[DType.uint8]](1)
        var ret = regexec(self._preg, c_text, 0, dummy, CInt(0))
        dummy.free()
        return ret == 0
