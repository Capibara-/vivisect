#include <errno.h>
#include <stdint.h>

#include "wireconst.h"

#define WT_VERSION  0x00000001

/* one meg packet max */
#define MSGMAX   1024000 // msg max data size

//#define WT_MSG_HELO     htonl('helo')  // hello / info
//#define WT_MSG_DERP     htonl('derp')  // i dont understand msg type

// processes / attach / detach
//#define WT_MSG_PS       'psls'  // list processes
//#define WT_MSG_ATTACH   'atch'  // attach to a process
//#define WT_MSG_DETACH   'dtch'  // detach from a process

// peek / poke
//#define WT_MSG_READREG  'rreg'  // read reg ctx
//#define WT_MSG_WRITEREG 'wreg'  // write reg ctx
//#define WT_MSG_MEMMAPS  'mmap'  // list memory maps
//#define WT_MSG_READMEM  'rmem'  // read memory
//#define WT_MSG_WRITEMEM 'wmem'  // write memory
//#define WT_MSG_ALLOCMEM 'amem'  // allocate memory

// threads related messages
//#define WT_MSG_THREADS  'lthr'  // list threads
//#define WT_MSG_THREAD   'sthr'  // select a thread

//#define WT_MSG_READFILE 'rfil'  // read file contents

#define WT_ERR_OK           0
#define WT_ERR_SOCKCLOSE    1
#define WT_ERR_MSGMAX       2
#define WT_ERR_PROCMAX      3
#define WT_ERR_INIT         0xffffffff

#define WT_ERRNO_MASK       0xc0000000

/* build env options */
#define WT_OPT_FORKING      1
#define ARCHSTR "i386"
#define PLATSTR "linux"

/* to allow platform variants... */
typedef uint32_t    wt_err_t;
typedef int         wt_sock_t;
typedef uint8_t     wt_byte_t;
typedef uint32_t    wt_size_t;
typedef uint8_t *   wt_bytes_t;

typedef struct wt_msg {
    uint32_t    type;
    uint32_t    flag;
    uint32_t    size;
} wt_msg_t;

typedef struct wt_msg_helo {
    uint32_t    arch;
    uint32_t    flags;
} wt_msg_helo_t;

typedef struct wt_msg_atch {
    uint32_t pid;
} wt_msg_atch_t;

typedef struct wt_msg_dtch {
    uint32_t pid;
} wt_msg_dtch_t;

typedef struct wt_msg_erro {
    uint32_t    err;
    char        msg[];
} wt_msg_erro_t;

/* context of a connected client */
typedef struct wt_ctx {
    wt_msg_t    msg;
    wt_err_t    err;
    union {
        wt_bytes_t      bytes;
        wt_msg_helo_t  *helo;
        wt_msg_atch_t  *atch;
        wt_msg_dtch_t  *dtch;
        wt_msg_erro_t  *erro;
    } msgbody;
    wt_sock_t   sock;
} wt_ctx_t;

/* l1iberty is going to hate these.. ;) */
#define WT_ENTRY        wt_err_t wterr = WT_ERR_INIT;
#define WT_SUCCESS      wterr = WT_ERR_OK;
#define WT_CLEANUP      wtclean:
#define WT_RETURN       return(wterr);
#define WT_GTFO()       goto wtclean;

#define WT_BAILING      (wterr != WT_ERR_OK && wterr != WT_ERR_INIT)

#define WT_BAIL(y)      { wterr = y; printf("bail: %d %s\n", __LINE__, __FILE__); goto wtclean; }
#define WT_BAIL_ERRNO() WT_BAIL(errno | WT_ERRNO_MASK)

#define WT_CALL(x)  wterr = (x); if ( WT_BAILING ) goto wtclean;
