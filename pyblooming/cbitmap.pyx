from libc cimport stdlib
import os.path

cdef extern from "cbitmaputil.h" nogil:
    cdef int grow_file(int filedes, int len)
    cdef char* mmap_file(int filedes, int len)
    cdef int mummap_file(char* addr, int len)
    cdef int flush(int filedes, char* addr, int len)

cdef class Bitmap:
    cdef object fileobj
    cdef int size
    cdef int fileno
    cdef unsigned char* mmap

    def __cinit__(self, length, filename=None):
        """
        Creates a new Bitmap object. Bitmap wraps a memory mapped
        file and allows bit-level operations to be performed.
        A bitmap can either be created on a file, or using an anonymous map.

        :Parameters:
            length : The length of the Bitmap in bytes. The number of bits is 8 times this.
            filename (optional) : Defaults to None. If this is provided, the Bitmap will be file backed.
        """
        # Check the length
        if length <= 0: raise ValueError, "Length must be positive!"
        self.size = length

        # Create the fileobj and mmap
        if not filename:
            self.fileobj = None
            self.fileno = -1
            self.mmap = <unsigned char*>mmap_file(self.fileno, self.size)
            if self.mmap == NULL:
                raise OSError, "Failed to create memory mapped region!"
        else:
            self.fileobj = open(filename, "a+")
            self.fileno = self.fileobj.fileno()

            # Grow the file if needed
            if os.path.getsize(filename) < length:
                if grow_file(self.fileno, self.size) == -1:
                    self.fileobj.close()
                    raise OSError, "Failed to grow file size!"

            # Create the memory mapped file
            self.mmap = <unsigned char*>mmap_file(self.fileno, self.size)
            if self.mmap == NULL:
                self.fileobj.close()
                raise OSError, "Failed to memory map the file!"

    def __len__(self):
        "Returns the size of the Bitmap in bits"
        return 8 * self.size

    def __getitem__(self, unsigned int idx):
        "Gets the value of a specific bit. Must take an integer argument"
        cdef unsigned char byte_val = self.mmap[idx >> 3]
        return <int> (byte_val >> (7 - idx % 8)) & 0x1

    def __setitem__(self, unsigned int idx, unsigned int val):
        """
        Sets the value of a specific bit. The index must be an integer,
        but if val evaluates to True, the bit is set to 1, else 0.
        """
        cdef unsigned char byte_val = self.mmap[idx >> 3]
        if val:
            self.mmap[idx >> 3] = byte_val | 1 << (7 - idx % 8)
        else:
            self.mmap[idx >> 3] = byte_val & ~(1 << (7 - idx % 8))

    def flush(self):
        "Flushes the contents of the Bitmap to disk."
        if flush(self.fileno, <char*>self.mmap, self.size) == -1:
            raise OSError, "Failed to flush the buffers!"

    def close(self):
        "Closes the Bitmap, first flushing the data."
        # Safety first!
        self.flush()

        # Close the mmap
        if self.mmap:
            mummap_file(<char*>self.mmap, self.size)
            self.mmap = None

        # For non-anonymous maps, we need to close the file
        if self.fileobj:
            self.fileobj.close()
            self.fileobj = None

    def __getslice__(self, i, j):
        "Allow direct access to the mmap, indexed by byte"
        if i > j or i < 0 or j > self.size: raise ValueError, "Bad slice!"
        # Create a null terminated string
        return self.mmap[i:j]

    def __setslice__(self, i, j, char* val):
        "Allow direct access to the mmap, indexed by byte"
        if i > j or i < 0 or j > self.size: raise ValueError, "Bad slice!"
        # Create a null terminated string
        cdef int size  = j-i
        cdef int x
        for x in xrange(size):
            self.mmap[i+x] = val[x]


