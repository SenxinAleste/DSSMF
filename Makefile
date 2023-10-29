CC			:= gcc
CFLAGS		:= -O2 -Wall -I./include
LDFLAGS		:= -L../lib -lm
SRC			:= ./src/cnx_to_smf.c ./src/decomp_cnx.c ./src/filename_util.c
HDR			:= convert_cnx.h filename_util.h
OBJS		:= $(patsubst %.c,%.o,$(SRC))
DEPS		:= $(patsubst %.c,%.d,$(SRC))
OUTPUT		:= ./bin/cnx_to_smf
UNAME		:= $(shell uname | tr '[:lower:]' '[:upper:]')

.PHONY: all
all: $(OUTPUT)

.PHONY: run
run: $(OUTPUT)
	./$^

-include $(DEPS)

$(OUTPUT): $(OBJS)
	$(CC) -o $@ $^ $(LDFLAGS)

%.o: %.c
	$(CC) -c $(CFLAGS) $< -o $@

.PHONY: clean
clean:
	$(RM) -f $(DEPS) $(OBJS) $(OUTPUT) $(addsuffix .exe,$(OUTPUT))
