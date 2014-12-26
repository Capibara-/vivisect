#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>

#include <fcntl.h>
#include <dirent.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

#include <sys/ptrace.h>

#include "wirestub.h"

#define SA  struct sockaddr

wt_err_t recvsize(wt_sock_t sock, wt_size_t size, wt_bytes_t bytes) {
    WT_ENTRY;

    wt_size_t   x = 0;
    wt_size_t   sofar = 0;

    while ( sofar < size ) {
        x = recv( sock, bytes + sofar, size - sofar, 0);
        if ( x == 0 ) WT_BAIL(WT_ERR_SOCKCLOSE);
        sofar += x;
    }

    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}

wt_err_t sendsize(wt_sock_t sock, wt_size_t size, void *bytes) {
    WT_ENTRY;

    wt_size_t   x = 0;
    wt_size_t   sofar = 0;

    while ( sofar < size ) {
        x = send( sock, bytes + sofar, size - sofar, 0);
        if ( x == -1 ) WT_BAIL(WT_ERR_SOCKCLOSE);
        sofar += x;
    }
    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}

wt_err_t init_listener( int port, wt_sock_t *listn ) {

    WT_ENTRY;

    int x = 0;
    struct sockaddr_in sin = {0};

    sin.sin_port = htons(port);
    sin.sin_family = AF_INET;

    *listn = socket(AF_INET, SOCK_STREAM, 0);
    if ( *listn == -1 ) WT_BAIL_ERRNO();

    x = bind(*listn, (SA*)&sin, sizeof(SA));
    if ( x != 0 ) WT_BAIL_ERRNO();

    x = listen(*listn, 20);
    if ( x != 0 ) WT_BAIL_ERRNO();


    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}

wt_err_t send_msg(wt_ctx_t *ctx, uint32_t type, uint32_t flag, uint32_t size, wt_bytes_t body) {
    WT_ENTRY;

    wt_msg_t msg = {0};

    msg.type = type;
    msg.flag = flag;
    msg.size = size;

    WT_CALL( sendsize( ctx->sock, sizeof(msg), &msg) );
    WT_CALL( sendsize( ctx->sock, size, body ) );

    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}

wt_err_t send_errno(wt_ctx_t *ctx) {
    WT_ENTRY;

    wt_msg_t msg = {0};

    wt_err_t myerr = errno;
    char *errstr = strerror(myerr);
    wt_size_t errlen = strlen(errstr);

    msg.type = WT_MSG_ERRO;
    msg.size = errlen + sizeof(wt_err_t);

    WT_CALL( sendsize( ctx->sock, sizeof(msg), &msg) );
    WT_CALL( sendsize( ctx->sock, sizeof(wt_err_t), &myerr) );
    WT_CALL( sendsize( ctx->sock, errlen, errstr ) );

    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}

wt_err_t handle_msg_atch( wt_ctx_t *ctx ) {
    WT_ENTRY;

    printf("attach: %d\n", ctx->msgbody.atch->pid);
    long pt = ptrace(PT_ATTACH, ctx->msgbody.atch->pid, 0, 0);
    if ( pt == 0 ) {
        WT_CALL( send_msg(ctx, WT_MSG_ATCH, 0, 0, NULL) );
    } else {
        WT_CALL( send_errno(ctx) );
    }

    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}

wt_err_t handle_msg_dtch( wt_ctx_t *ctx ) {
    WT_ENTRY;

    printf("detach: %d\n", ctx->msgbody.dtch->pid);
    long pt = ptrace(PT_DETACH, ctx->msgbody.dtch->pid, 0, 0);
    if ( pt == 0 ) {
        WT_CALL( send_msg(ctx, WT_MSG_DTCH, 0, 0, NULL) );
    } else {
        WT_CALL( send_errno(ctx) );
    }

    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}

wt_err_t handle_msg_file( wt_ctx_t *ctx ) {
    WT_ENTRY;

    int x = 0;
    int fd = -1;
    wt_msg_t msg = {0};
    struct stat fdstat = {0};

    fd = open(ctx->msgbody.bytes,O_RDONLY);
    if ( fd == -1 ) {
        WT_CALL( send_errno(ctx) );
        WT_GTFO();
    }

    if ( fstat(fd,&fdstat) != 0 ) {
        WT_CALL( send_errno(ctx) );
        WT_GTFO();
    }

    msg.type = WT_MSG_FILE;
    msg.size = fdstat.st_size;

    /* /proc files have no st_size... */
    if ( fdstat.st_size == 0 ) {
        x = read(fd, ctx->msgbody.bytes, MSGMAX);
        if ( x == MSGMAX ) WT_BAIL(WT_ERR_PROCMAX);
        /* proc like file... hopefully fit in MSGMAX */
        msg.size = x;
        WT_CALL( sendsize(ctx->sock, sizeof(msg), &msg) );
        WT_CALL( sendsize(ctx->sock, x, ctx->msgbody.bytes) );
        WT_GTFO();
    }

    WT_CALL( sendsize(ctx->sock, sizeof(msg), &msg) );

    while ( ! WT_BAILING ) {
        x = read(fd, ctx->msgbody.bytes, MSGMAX);
        if ( x == 0 )
            break;

        WT_CALL( sendsize(ctx->sock, x, ctx->msgbody.bytes) );
    }

    WT_SUCCESS;

    WT_CLEANUP;
      close(fd);

    WT_RETURN;
}

wt_err_t handle_msg_ldir( wt_ctx_t *ctx ) {
    WT_ENTRY;

    wt_size_t off = 0;
    wt_size_t size = 0;
    DIR *dir = opendir( ctx->msgbody.bytes );
    struct dirent *dent = NULL;

    if ( dir == NULL ) {
        WT_CALL( send_errno(ctx) );
        WT_GTFO();
    }

    while ( ! WT_BAILING ) {
        dent = readdir(dir);
        if ( dent == NULL )
            break;

        size = strlen( dent->d_name ) + 1;
        if ( off + size  > MSGMAX )
            break;

        memcpy(ctx->msgbody.bytes + off, dent->d_name, size);
        off += size;
    }

    WT_CALL( send_msg(ctx, WT_MSG_LDIR, 0, off, ctx->msgbody.bytes) );
    
    WT_SUCCESS;
    WT_CLEANUP;
        if ( dir != NULL ) closedir(dir);
    WT_RETURN;
}

wt_err_t handle_message( wt_ctx_t *ctx ) {
    WT_ENTRY;

    printf("msg: %.8x\n", ctx->msg.type);

    switch ( ctx->msg.type ) {

        case WT_MSG_HELO:
            WT_CALL( send_msg(ctx, WT_MSG_HELO, 0, sizeof(wt_msg_helo_t), ctx->msgbody.bytes) );
            break;

        case WT_MSG_ARCH:
            WT_CALL( send_msg(ctx, WT_MSG_ARCH, 0, strlen(ARCHSTR), (wt_bytes_t)ARCHSTR) );
            break;

        case WT_MSG_PLAT:
            WT_CALL( send_msg(ctx, WT_MSG_PLAT, 0, strlen(PLATSTR), (wt_bytes_t)PLATSTR) );
            break;

        case WT_MSG_FILE:
            WT_CALL( handle_msg_file( ctx ) );
            break;

        case WT_MSG_LDIR:
            WT_CALL( handle_msg_ldir( ctx ) );
            break;

        case WT_MSG_ATCH:
            WT_CALL( handle_msg_atch( ctx ) );
            break;

        case WT_MSG_DTCH:
            WT_CALL( handle_msg_dtch( ctx ) );
            break;

        default:
            WT_CALL( send_msg(ctx, WT_MSG_DERP, 0, 0, NULL) );
            break;

    }
    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}

wt_err_t handle_socket( wt_sock_t sock ) {
    WT_ENTRY;

    wt_ctx_t    ctx = {0};

    ctx.sock = sock;
    ctx.msgbody.bytes = malloc(MSGMAX);

    while ( ! WT_BAILING ) {
        WT_CALL( recvsize( sock, sizeof(wt_msg_t), (wt_bytes_t)(&ctx.msg) ));

        /* check against max msg size */
        if (ctx.msg.size > MSGMAX)
            WT_BAIL(WT_ERR_MSGMAX);

        WT_CALL( recvsize( sock, ctx.msg.size, ctx.msgbody.bytes ));
        WT_CALL( handle_message( &ctx ) );
    }

    WT_SUCCESS;
    WT_CLEANUP;

    shutdown(sock, SHUT_RDWR);
    close(sock);

    if ( ctx.msgbody.bytes != NULL )
        free(ctx.msgbody.bytes);

    WT_RETURN;
}


wt_err_t server_loop( wt_sock_t listn ) {
    WT_ENTRY;

    wt_sock_t sock = 0;

    int sinlen = sizeof(SA);
    struct sockaddr_in sin = {0};

    while ( ! WT_BAILING ) {
        sock = accept( listn, (SA*)&sin, &sinlen);
        if ( sock == -1 ) WT_BAIL_ERRNO();

#ifdef WT_OPT_FORKING
        if ( fork() != 0 ) {
            // the parent
            close(sock);
            continue;
        }
        // the child
        close(listn);
        WT_CALL( handle_socket(sock) );
        exit(0);
#endif
        WT_CALL( handle_socket(sock) );
    }

    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}

wt_err_t run_server() {
    WT_ENTRY;

    wt_sock_t listn = 0;
    WT_CALL( init_listener( 9999, &listn ) );
    WT_CALL( server_loop( listn ) );

    WT_SUCCESS;
    WT_CLEANUP;
    WT_RETURN;
}


int main(int argc, char **argv) {
    printf("wirestub: %.8x\n", WT_VERSION);
    run_server();
    return(0);
}

