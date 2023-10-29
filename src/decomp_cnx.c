#include <stdio.h>
#include <stdlib.h>

#include "decomp_cnx.h"


int decomp_CNX_file(const char *cnx_filepath, const char *decomp_filename)
{
    // CNX�t�@�C�����J��
    FILE* cnx_fp = fopen(cnx_filepath, "rb");
    if (cnx_fp == NULL) {
      fprintf(stderr, "Failed to open file: %s\n", cnx_filepath);
        return EXIT_FAILURE;
    }

    // CNX�t�@�C����ǂݍ��ޗ̈�
    const uint cnx_data_size = 0x10000;
    uchar *cnx_data = calloc(cnx_data_size, 1);
    if (cnx_data == NULL) {
        fprintf(stderr, "Failed to calloc.\n");
        return EXIT_FAILURE;
    }

    fread(cnx_data, 1, cnx_data_size, cnx_fp);
    fclose(cnx_fp);

    // CNX���ʎq�`�F�b�N
    if ((*cnx_data != 'C') 
        || (cnx_data[1] != 'N') 
        || (cnx_data[2] != 'X') 
        || (cnx_data[3] != '\x02')) {
        fprintf(stderr, "No CNX identifier.\n");
        return EXIT_FAILURE;
    }

    // �𓀌�T�C�Y���v�Z
    uint decomp_size_raw = *(uint *)(cnx_data + 0xc);
    uint decomp_size = 
        ((decomp_size_raw & 0xff00) | decomp_size_raw << 0x10) << 8
        |
        (decomp_size_raw >> 0x10 & 0xff) << 8
        |
        decomp_size_raw >> 0x18;
    fprintf(stdout, "- decomp_size: %x\n", decomp_size);

    // �𓀌�f�[�^���������ޗ̈�
    uchar *decomp_data = calloc(decomp_size, 1);
    if (decomp_data == NULL) {
        fprintf(stderr, "Failed to calloc.\n");
        free(cnx_data);
        return EXIT_FAILURE;
    }

    // ��
    for (uint counter = 0; counter < decomp_size; ) {
        int res = decomp_memory_area(decomp_data, cnx_data + CNX_HEADER_SIZE, 0, &counter);
        fprintf(stdout, "- Decompress completed: code=%x, %x/%x\n", res, counter, decomp_size);
    }

    // ��������
    FILE *decomp_fp = fopen(decomp_filename, "wb");
    if (fwrite(decomp_data, 1, decomp_size, decomp_fp) != (size_t)decomp_size) {
        fprintf(stderr, "Failed to write: %s\n", decomp_filename);

        free(decomp_data);
        free(cnx_data);

        return EXIT_FAILURE;
    }
    fclose(decomp_fp);

    // �̈�̉��
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

  // ���[�v�J�n
  do {
    // ��2bit�Ŕ��f
    switch((uint)compress_flag & 3) {
    case 0:
      ++cnx_data_current_buf;
      compress_counter = 4;
      cnx_data_cur += *cnx_data_cur + 1;
      
      // �I�����m�H
      /*
      if ((num != 0) && (num <= (int)cnx_data_current_buf)) { //��΂ɐ������Ȃ��H
        D�V�^�̈擪_004e6200 = decomp_data_cur; //����K�Ɉړ�
        D�V�l0x10_004e6204
          = cnx_data_cur + ((int)D�V�l0x10_004e6204 - (int)cnx_data_body);
            //�ǂݍ��݃o�C�g��+0x10�A�܂�SMF���f�[�^�i�]�v�w�b�_�܂ށj�̒���
        *counter
          = decomp_data_cur + ((int)*counter - (int)decomp_data);
            //�������݃o�C�g���i�V�����񂽂̏����l��0�ׁ̈j
        D�VSMF������_004e6210 = cnx_data_cur; //����K�Ɉړ�
        // �W�J�̓R�[�h1�ŏI��
        return 1;
      }
      */
      break;
    case 1:
      // ���̂܂܎ʂ�����
      *decomp_data_cur = *cnx_data_cur;
      // �ǂݏ����i�߂�
      ++decomp_data_cur;
      ++cnx_data_cur;
      break;
    case 2:
      // ���o�C�g�ǂݍ���
      read_byte = *cnx_data_cur;
      // �ǎ擪��1�o�C�g��A�h���X
      next_byte = cnx_data_cur + 1;
      // �ǎ擪��2�o�C�g��A�h���X
      cnx_data_cur += 2;
      ushort con = read_byte << 0x8 | *next_byte;
      decomp_part_len = (con & 0x1f) + 4;
      decomp_part(
        decomp_data_cur,
        decomp_data_cur + (-1 - (uint)(ushort)(con >> 5)),
        decomp_part_len
      );
      // �����i�߂�
      decomp_data_cur += decomp_part_len;
      break;
    case 3:
      // ���[�v�񐔐ݒ�
      loop_count = (uint)*cnx_data_cur;
      // �ǂݐi�߂�
      while (++cnx_data_cur, loop_count != 0) {
        // ���̂܂܎ʂ�����
        *decomp_data_cur = *cnx_data_cur;
        // �����i�߂�
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

      // �I�����m�H
      if (compress_flag == 0x0) {
        *counter = (int)decomp_data_cur + ((int)*counter - (int)decomp_data);
        // �W�J�̓R�[�h2�ŏI��
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
            // �������ݒ�
            *decomp_data_top = *(char *)((int)decomp_data_top + diff);
            // �����i�߂�
            ++decomp_data_top;
        }
    }
    
    return;
}
