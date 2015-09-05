[Version]
1.2.3.4

[Parameters]
Resist i-line
Unknown
0
1
0

[Comments]
Example of test i-line (365 nm) photoresist file 

[Develop Parameters]
1
3							;Dev model (1=Mack, 2=Enhanced, 3=Notch)
User Defined
105.0						;Development Rmax (nm/s)
0.025						;Development Rmin (nm/s)
1.500						;Development n
0.700						;Development Notch Mth
13.500						;Development Notch n
1.000
10.000

[PAB Parameters]
1
1000.000
1.000

[PEB Parameters]
1
32.50						;PEB Diffusivity Ea (kcal/mole)
46.000						;PEB Diffusivity Ln(Ar) (nm2/s)


;wavelength    A      B      C      Unexposed n   Completely Exposed n
;   (nm)     (1/um) (1/um) (cm2/mJ)
[Exposure Parameters]
1						
365.000  0.800  0.040  0.010  1.5  1.5
