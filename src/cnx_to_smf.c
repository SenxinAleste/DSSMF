#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "filename_util.h"
#include "decomp_cnx.h"

#define FILEPATH_LEN_MAX 320
#define FILENAME_LEN_MAX 24



int main(int argc, char **argv)
{
    // ファイルリスト読み込み
    char cnx_list_filepaths[] = "cnx_list.txt";

    FILE *fp = fopen(cnx_list_filepaths, "rt");
    if (fp == NULL) {
        fprintf(stderr, "Failed to open file: %s\n", cnx_list_filepaths);
        exit(EXIT_FAILURE);
    }

    char cnx_filepath[FILEPATH_LEN_MAX];
    while (fgets(cnx_filepath, FILEPATH_LEN_MAX, fp) != NULL) {
        // 個別のCNX式ファイル読み込み
        size_t n = strlen(cnx_filepath);
        if (cnx_filepath[n - 1] == '\n') {
            cnx_filepath[n - 1] = '\0';
        }
        
        char cnx_filename[FILENAME_LEN_MAX];
        if (get_filename(cnx_filepath, cnx_filename, sizeof(cnx_filename), '\\') != EXIT_SUCCESS) {
            fprintf(stderr, "Failed to find filename. : %s\n", cnx_filepath);
            continue;
        }

        // 解凍実行
        fprintf(stdout, "Decompress: %s\n", cnx_filepath);
        if (decomp_CNX_file(cnx_filepath, cnx_filename) != EXIT_SUCCESS) {
            fprintf(stderr, "Failed to decompress %s\n", cnx_filepath);
            continue;
        }
    }

    // ファイルを閉じる
    if (fclose(fp) != 0) {
        fprintf(stderr, "Failed to close %s.\n", cnx_list_filepaths);
        exit(EXIT_FAILURE);
    }

    return EXIT_SUCCESS;
}