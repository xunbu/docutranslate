/**
 * 共享的 body 滚动锁。
 *
 * 以前 Modal/Offcanvas 各自直接改 `document.body.style.overflow`：watch 没有
 * immediate（挂载时已打开则不锁），也没有 onUnmounted 复位（卸载时保持 hidden），
 * 多个弹窗互相覆盖状态。用一个计数器让嵌套弹窗也能正确恢复。
 */
let openCount = 0
let previousOverflow = ''

export function lockBodyScroll() {
    if (openCount === 0) {
        previousOverflow = document.body.style.overflow
        document.body.style.overflow = 'hidden'
    }
    openCount += 1
}

export function unlockBodyScroll() {
    if (openCount === 0) return
    openCount -= 1
    if (openCount === 0) {
        document.body.style.overflow = previousOverflow
    }
}
