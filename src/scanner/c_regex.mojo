from sys import external_call
from memory import UnsafePointer

# POSIX Regex Constants
alias REG_EXTENDED = 1
alias REG_ICASE    = 2
alias REG_NOSUB    = 4
alias REG_NEWLINE  = 8

alias REGEX_T_SIZE = 128

# Use Scalar[DType.uint8] for byte pointers
alias VoidPtr = UnsafePointer[Scalar[DType.uint8]]
alias CharPtr = UnsafePointer[Scalar[DType.int8]]

fn regcomp(preg: VoidPtr, pattern: CharPtr, cflags: Int32) -> Int32:
    return external_call["regcomp", Int32](preg, pattern, cflags)

fn regexec(preg: VoidPtr, string: CharPtr, nmatch: Int, pmatch: VoidPtr, eflags: Int32) -> Int32:
    return external_call["regexec", Int32](preg, string, nmatch, pmatch, eflags)

fn regfree(preg: VoidPtr):
    external_call["regfree", NoneType](preg)

struct Regex:
    var _preg: VoidPtr
    var _pattern: String
    var _initialized: Bool

    fn __init__(out self, pattern: String):
        # Use alloc on the type alias or UnsafePointer type
        self._preg = VoidPtr.alloc(REGEX_T_SIZE)
        self._pattern = pattern
        self._initialized = False
        
        # Create a null-terminated string buffer manually if needed, 
        # but unsafe_cstr_ptr() usually returns a valid pointer.
        # We use as_c_string_slice() if unsafe_cstr_ptr is deprecated?
        # The warning said: Use `String.as_c_string_slice()` instead.
        # This likely returns a Slice, we need the pointer.
        
        var p_copy = pattern
        # unsafe_cstr_ptr() returns UnsafePointer[Scalar[DType.int8]] usually (CharPtr)
        var c_pattern = p_copy.unsafe_cstr_ptr()
        
        var ret = regcomp(self._preg, c_pattern, Int32(REG_EXTENDED | REG_NOSUB | REG_ICASE))
        if ret == 0:
            self._initialized = True
        else:
            print("Regex compilation failed for: " + pattern)

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
        var c_text = t_copy.unsafe_cstr_ptr()
        # 0 matches
        var ret = regexec(self._preg, c_text, 0, VoidPtr(), Int32(0))
        return ret == 0
