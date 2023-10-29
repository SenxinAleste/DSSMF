#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "filename_util.h"

int get_filename(const char *filepath, char *filename, size_t filename_len, char delimiter)
{
    char *dir_end=NULL;

    if ((filepath == NULL) || (filename==NULL))
    {
        return EXIT_FAILURE;
    }

    dir_end = strrchr(filepath, delimiter);
    if (dir_end == NULL)
    {
        return EXIT_FAILURE;
    }

    snprintf(filename, filename_len, "%s", dir_end + 1);

    return EXIT_SUCCESS;
}