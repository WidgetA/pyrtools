#define FBC_EXPORTS __declspec(dllexport)

FBC_EXPORTS void internal_pointop(double *im, double *res, int size, double *lut,
		      int lutsize, double origin, double increment, 
		      int warnings);
