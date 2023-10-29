#ifndef _DECOMP_CNX_H
#define _DECOMP_CNX_H

typedef unsigned char uchar;
typedef unsigned short ushort;
typedef unsigned int uint;

#define CNX_HEADER_SIZE 0x10

int decomp_CNX_file(const char *cnx_filepath, const char *decomp_filename);
int decomp_memory_area(uchar *decomp_data, uchar *cnx_data, int num, uint *counter);
void decomp_part(uchar *decomp_data_top, uchar *decomp_data_middle, int loop_max);

#endif