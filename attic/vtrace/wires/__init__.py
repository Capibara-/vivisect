'''
One wire module for each supported vtrace platform.  Wire modules are
allowed to be highly platform specific ( and may not even import cleanly
on other platforms ).  Therefor, any dependant code *must* dynamically
import the wire modules based on platform detection.
'''
