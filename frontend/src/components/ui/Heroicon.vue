<script setup>
import { computed } from 'vue';
import {
    DocumentIcon,
    DocumentTextIcon,
    DocumentArrowDownIcon,
    ArchiveBoxArrowDownIcon,
    CodeBracketIcon,
    TableCellsIcon,
    BookOpenIcon,
    ArrowDownTrayIcon,
    ArrowUpTrayIcon,
    ArrowTopRightOnSquareIcon,
    PaperClipIcon,
    LinkIcon,
    LinkSlashIcon,
    QuestionMarkCircleIcon,
    Cog6ToothIcon,
    UserGroupIcon,
    LanguageIcon,
    ChevronDownIcon,
    XMarkIcon,
    Bars3Icon,
    SunIcon,
    MoonIcon,
    ComputerDesktopIcon,
    CheckIcon,
    ExclamationCircleIcon,
    InformationCircleIcon,
    PlayIcon,
    PauseIcon,
    StopIcon,
    ArrowPathIcon,
    EyeIcon,
    ClipboardDocumentIcon,
    ClipboardDocumentListIcon,
    FolderOpenIcon,
    PlusIcon,
    TrashIcon,
    CloudArrowUpIcon,
    CommandLineIcon,
    EyeSlashIcon,
    SparklesIcon
} from '@heroicons/vue/24/outline';

import {
    DocumentIcon as DocumentIconSolid,
    DocumentTextIcon as DocumentTextIconSolid,
    QuestionMarkCircleIcon as QuestionMarkCircleIconSolid,
    UserGroupIcon as UserGroupIconSolid,
    CheckIcon as CheckIconSolid,
    XMarkIcon as XMarkIconSolid,
    ExclamationCircleIcon as ExclamationCircleIconSolid,
    CheckCircleIcon as CheckCircleIconSolid
} from '@heroicons/vue/24/solid';

const props = defineProps({
    name: {
        type: String,
        required: true
    },
    solid: {
        type: Boolean,
        default: false
    },
    class: {
        type: String,
        default: 'w-5 h-5'
    }
});

const iconComponents = {
    'DocumentIcon': { outline: DocumentIcon, solid: DocumentIconSolid },
    'DocumentTextIcon': { outline: DocumentTextIcon, solid: DocumentTextIconSolid },
    'DocumentArrowDownIcon': { outline: DocumentArrowDownIcon, solid: DocumentArrowDownIcon },
    'ArchiveBoxArrowDownIcon': { outline: ArchiveBoxArrowDownIcon, solid: ArchiveBoxArrowDownIcon },
    'CodeBracketIcon': { outline: CodeBracketIcon, solid: CodeBracketIcon },
    'TableCellsIcon': { outline: TableCellsIcon, solid: TableCellsIcon },
    'BookOpenIcon': { outline: BookOpenIcon, solid: BookOpenIcon },
    'ArrowDownTrayIcon': { outline: ArrowDownTrayIcon, solid: ArrowDownTrayIcon },
    'ArrowUpTrayIcon': { outline: ArrowUpTrayIcon, solid: ArrowUpTrayIcon },
    'ArrowTopRightOnSquareIcon': { outline: ArrowTopRightOnSquareIcon, solid: ArrowTopRightOnSquareIcon },
    'PaperClipIcon': { outline: PaperClipIcon, solid: PaperClipIcon },
    'LinkIcon': { outline: LinkIcon, solid: LinkIcon },
    'LinkSlashIcon': { outline: LinkSlashIcon, solid: LinkSlashIcon },
    'QuestionMarkCircleIcon': { outline: QuestionMarkCircleIcon, solid: QuestionMarkCircleIconSolid },
    'Cog6ToothIcon': { outline: Cog6ToothIcon, solid: Cog6ToothIcon },
    'UserGroupIcon': { outline: UserGroupIcon, solid: UserGroupIconSolid },
    'LanguageIcon': { outline: LanguageIcon, solid: LanguageIcon },
    'ChevronDownIcon': { outline: ChevronDownIcon, solid: ChevronDownIcon },
    'XMarkIcon': { outline: XMarkIcon, solid: XMarkIconSolid },
    'Bars3Icon': { outline: Bars3Icon, solid: Bars3Icon },
    'SunIcon': { outline: SunIcon, solid: SunIcon },
    'MoonIcon': { outline: MoonIcon, solid: MoonIcon },
    'ComputerDesktopIcon': { outline: ComputerDesktopIcon, solid: ComputerDesktopIcon },
    'CheckIcon': { outline: CheckIcon, solid: CheckIconSolid },
    'CheckCircleIcon': { outline: CheckIcon, solid: CheckCircleIconSolid },
    'ExclamationCircleIcon': { outline: ExclamationCircleIcon, solid: ExclamationCircleIconSolid },
    'InformationCircleIcon': { outline: InformationCircleIcon, solid: InformationCircleIcon },
    'PlayIcon': { outline: PlayIcon, solid: PlayIcon },
    'PauseIcon': { outline: PauseIcon, solid: PauseIcon },
    'StopIcon': { outline: StopIcon, solid: StopIcon },
    'ArrowPathIcon': { outline: ArrowPathIcon, solid: ArrowPathIcon },
    'EyeIcon': { outline: EyeIcon, solid: EyeIcon },
    'EyeSlashIcon': { outline: EyeSlashIcon, solid: EyeSlashIcon },
    'ClipboardDocumentIcon': { outline: ClipboardDocumentIcon, solid: ClipboardDocumentIcon },
    'ClipboardDocumentListIcon': { outline: ClipboardDocumentListIcon, solid: ClipboardDocumentListIcon },
    'FolderOpenIcon': { outline: FolderOpenIcon, solid: FolderOpenIcon },
    'PlusIcon': { outline: PlusIcon, solid: PlusIcon },
    'TrashIcon': { outline: TrashIcon, solid: TrashIcon },
    'CloudArrowUpIcon': { outline: CloudArrowUpIcon, solid: CloudArrowUpIcon },
    'CommandLineIcon': { outline: CommandLineIcon, solid: CommandLineIcon },
    'SparklesIcon': { outline: SparklesIcon, solid: SparklesIcon }
};

const iconComponent = computed(() => {
    const icon = iconComponents[props.name];
    if (!icon) return DocumentIcon;
    return props.solid ? icon.solid : icon.outline;
});
</script>

<template>
    <component :is="iconComponent" :class="props.class" />
</template>
