"""
Implements a simple class to address individual bits using
a memory mapped file.
"""
import mmap
import os.path

class Bitmap(object):
    def __init__(self, length, anonymous=True, filename=None):
        """
        Creates a new Bitmap object. Bitmap wraps a memory mapped
        file and allows bit-level operations to be performed.
        A bitmap can either be created on a file, or using an anonymous map.

        :Parameters:
            length : The length of the Bitmap in bytes. The number of bits is 8 times this.
            anonymous (optional) : Defaults to True, if True there is no file backing store.
            filename (optional*) : Defaults to None. This must be provided if anonymous is False.
        """
        # Save if this is an anonymous mmap
        self.anonymous = anonymous
        self.size = length

        # Create the fileobj and mmap
        if anonymous:
            self.fileobj = None
            self.mmap = mmap.mmap(-1, length)
        else:
            if not filename: raise ValueError, "Must provide filename if anonymous is false!"
            self.fileobj = open(filename, "a+")

            # Write 0's to the file
            size_diff = length - os.path.getsize(filename)
            while size_diff > 0:
                self.fileobj.write(chr(0) * min(size_diff, 100000))
                self.fileobj.flush()
                size_diff = length - os.path.getsize(filename)

            # Create the memory mapped file
            self.mmap = mmap.mmap(self.fileobj.fileno(), length)

    def __len__(self):
        "Returns the size of the Bitmap in bits"
        return 8 * self.size

    def __getitem__(self, idx):
        "Gets the value of a specific bit. Must take an integer argument"
        if not isinstance(idx, (int, long)): raise TypeError, "Index be an integer type!"
        byte = idx / 8
        if byte < 0 or byte >= self.size: raise IndexError, "Index out of range!"

        byte_off  = 7 - idx % 8
        byte_val = ord(self.mmap[byte])
        return (byte_val >> byte_off) & 0x1

    def __setitem__(self, idx, val):
        """
        Sets the value of a specific bit. The index must be an integer,
        but if val evaluates to True, the bit is set to 1, else 0.
        """
        if not isinstance(idx, (int, long)): raise TypeError, "Index be an integer type!"
        byte = idx / 8
        if byte < 0 or byte >= self.size: raise IndexError, "Index out of range!"

        byte_off  = 7 - idx % 8
        byte_val = ord(self.mmap[byte])
        if val:
            byte_val |= 1 << byte_off
        else:
            byte_val &= ~(1 << byte_off)
        self.mmap[byte] = chr(byte_val)
        return val

    def flush(self):
        "Flushes the contents of the Bitmap to disk."
        if not self.anonymous: self.mmap.flush()
        if self.fileobj: self.fileobj.flush()

    def close(self):
        "Closes the Bitmap, first flushing the data."
        # Safety first!
        self.flush()

        # Close the mmap
        self.mmap.close()
        self.mmap = None

        # For non-anonymous maps, we need to close the file
        if self.fileobj:
            self.fileobj.close()
            self.fileobj = None

    def __or__(self, bitmap):
        "Implements a set union"
        if not isinstance(self, Bitmap): raise ValueError, "Cannot perform union with non-Bitmap"
        if self.size != bitmap.size: raise ValueError, "Cannot perform union with non-matching sizes!"
        bitmap = Bitmap(self.size)
        for i in xrange(self.size):
            bitmap.mmap[i] = chr(ord(self.mmap[i]) | ord(bitmap.mmap[i]))
        return bitmap

    def __and__(self, bitmap):
        "Implements a set intersection"
        if not isinstance(self, Bitmap): raise ValueError, "Cannot perform intersection with non-Bitmap"
        if self.size != bitmap.size: raise ValueError, "Cannot perform intersection with non-matching sizes!"
        bitmap = Bitmap(self.size)
        for i in xrange(self.size):
            bitmap.mmap[i] = chr(ord(self.mmap[i]) & ord(bitmap.mmap[i]))
        return bitmap
