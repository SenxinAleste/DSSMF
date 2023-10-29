#include <stdio.h>
#include <stdlib.h>

#include "decomp_cnx.h"


int decomp_CNX_file(const char *cnx_filepath, const char *decomp_filename)
{
    // CNXファイルを開く
    FILE* cnx_fp = fopen(cnx_filepath, "rb");
    if (cnx_fp == NULL) {
      fprintf(stderr, "Failed to open file: %s\n", cnx_filepath);
        return EXIT_FAILURE;
    }

    // CNXファイルを読み込む領域
    const uint cnx_data_size = 0x10000;
    uchar *cnx_data = calloc(cnx_data_size, 1);
    if (cnx_data == NULL) {
        fprintf(stderr, "Failed to calloc.\n");
        return EXIT_FAILURE;
    }

    fread(cnx_data, 1, cnx_data_size, cnx_fp);
    fclose(cnx_fp);

    // CNX識別子チェック
    if ((*cnx_data != 'C') 
        || (cnx_data[1] != 'N') 
        || (cnx_data[2] != 'X') 
        || (cnx_data[3] != '\x02')) {
        fprintf(stderr, "No CNX identifier.\n");
        return EXIT_FAILURE;
    }

    // 解凍後サイズを計算
    uint decomp_size_raw = *(uint *)(cnx_data + 0xc);
    uint decomp_size = 
        ((decomp_size_raw & 0xff00) | decomp_size_raw << 0x10) << 8
        |
        (decomp_size_raw >> 0x10 & 0xff) << 8
        |
        decomp_size_raw >> 0x18;
    fprintf(stdout, "- decomp_size: %x\n", decomp_size);

    // 解凍後データを書き込む領域
    uchar *decomp_data = calloc(decomp_size, 1);
    if (decomp_data == NULL) {
        fprintf(stderr, "Failed to calloc.\n");
        free(cnx_data);
        return EXIT_FAILURE;
    }

    // 解凍
    for (uint counter = 0; counter < decomp_size; ) {
        int res = decomp_memory_area(decomp_data, cnx_data + CNX_HEADER_SIZE, 0, &counter);
        fprintf(stdout, "- Decompress completed: code=%x, %x/%x\n", res, counter, decomp_size);
    }

    // 書き込み
    FILE *decomp_fp = fopen(decomp_filename, "wb");
    if (fwrite(decomp_data, 1, decomp_size, decomp_fp) != (size_t)decomp_size) {
        fprintf(stderr, "Failed to write: %s\n", decomp_filename);

        free(decomp_data);
        free(cnx_data);

        return EXIT_FAILURE;
    }
    fclose(decomp_fp);

    // 領域の解放
    free(decomp_data);
    free(cnx_data);

    return EXIT_SUCCESS;
}


int decomp_memory_area(uchar *decomp_data, uchar *cnx_data_body, int num, uint *counter)
{
    uchar *next_byte;
    uchar read_byte = *cnx_data_body;
    uint loop_count;
    uchar *decomp_data_cur = decomp_data;
    int compress_counter = 0;
    uchar *cnx_data_cur = cnx_data_body + 1;
    int decomp_part_len;

    uchar *cnx_data_current_buf = NULL;
    uchar compress_flag = read_byte;

  // ループ開始
  do {
    // 下2bitで判断
    switch((uint)compress_flag & 3) {
    case 0:
      ++cnx_data_current_buf;
      compress_counter = 4;
      cnx_data_cur += *cnx_data_cur + 1;
      
      // 終了検知？
      /*
      if ((num != 0) && (num <= (int)cnx_data_current_buf)) { //絶対に成立しない？
        Dシ真領域頭_004e6200 = decomp_data_cur; //頭を尻に移動
        Dシ値0x10_004e6204
          = cnx_data_cur + ((int)Dシ値0x10_004e6204 - (int)cnx_data_body);
            //読み込みバイト数+0x10、つまりSMF生データ（余計ヘッダ含む）の長さ
        *counter
          = decomp_data_cur + ((int)*counter - (int)decomp_data);
            //書き込みバイト数（シかうんたの初期値は0の為）
        DシSMF実実頭_004e6210 = cnx_data_cur; //頭を尻に移動
        // 展開はコード1で終了
        return 1;
      }
      */
      break;
    case 1:
      // そのまま写し書き
      *decomp_data_cur = *cnx_data_cur;
      // 読み書き進める
      ++decomp_data_cur;
      ++cnx_data_cur;
      break;
    case 2:
      // 生バイト読み込み
      read_byte = *cnx_data_cur;
      // 読取頭の1バイト先アドレス
      next_byte = cnx_data_cur + 1;
      // 読取頭の2バイト先アドレス
      cnx_data_cur += 2;
      ushort con = read_byte << 0x8 | *next_byte;
      decomp_part_len = (con & 0x1f) + 4;
      decomp_part(
        decomp_data_cur,
        decomp_data_cur + (-1 - (uint)(ushort)(con >> 5)),
        decomp_part_len
      );
      // 書き進める
      decomp_data_cur += decomp_part_len;
      break;
    case 3:
      // ループ回数設定
      loop_count = (uint)*cnx_data_cur;
      // 読み進める
      while (++cnx_data_cur, loop_count != 0) {
        // そのまま写し書き
        *decomp_data_cur = *cnx_data_cur;
        // 書き進める
        ++decomp_data_cur;

        --loop_count;
      }
    }
    
    ++compress_counter;
    
    if (compress_counter < 4) {
      compress_flag = (char)((int)compress_flag >> 2);
    }
    else {
      compress_counter = 0;
      compress_flag = *cnx_data_cur;
      ++cnx_data_cur;

      // 終了検知？
      if (compress_flag == 0x0) {
        *counter = (int)decomp_data_cur + ((int)*counter - (int)decomp_data);
        // 展開はコード2で終了
        return 2;
      }
    }
  } while( 1 );
}

void decomp_part(uchar *decomp_data_top, uchar *decomp_data_middle, int loop_max)
{
    if (0 < loop_max) {
        int diff = (int)decomp_data_middle;
        diff -= (int)decomp_data_top;
        
        for (int i = loop_max; i != 0; --i) {
            // 書き頭設定
            *decomp_data_top = *(char *)((int)decomp_data_top + diff);
            // 書き進める
            ++decomp_data_top;
        }
    }
    
    return;
}
