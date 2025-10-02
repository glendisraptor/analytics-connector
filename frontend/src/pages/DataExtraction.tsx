/* eslint-disable @typescript-eslint/no-explicit-any */
import { act, useEffect, useRef, useState } from "react";
import { Upload, FileText, Table as TableIcon, Plus, Eye, Trash2, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Select as ShadSelect,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    Select,
} from "@/components/ui/select";
import {
    Drawer,
    DrawerClose,
    DrawerContent,
    DrawerDescription,
    DrawerFooter,
    DrawerHeader,
    DrawerTitle,
} from "@/components/ui/drawer";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
// import { documentService } from "@/api/api";
import type { DocumentTable, DocumentField, DocumentResult } from "@/types";
import { documentService } from "@/services/api";

type ExtractionField = DocumentField;

type DataRow = {
    id: number;
    file: string;
    extractText: string;
    [key: string]: string | number;
};

const MODEL_OPTIONS = [
    { label: "Llama 3.1 8B", value: "llama-3.1-8b-instant" },
    { label: "Mixtral 8x7B", value: "mixtral-8x7b-32768" },
];

type StatusState = { type: "error" | "polling" | "success"; message: string } | null;

export default function DataExtraction() {
    const [selectedRow, setSelectedRow] = useState<DataRow | null>(null);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);

    const [tables, setTables] = useState<DocumentTable[]>([]);
    const [currentTable, setCurrentTable] = useState<string>("");
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isConfigDrawerOpen, setIsConfigDrawerOpen] = useState(false);
    const [extractionFields, setExtractionFields] = useState<ExtractionField[]>([]);
    const [isNewTableDialogOpen, setIsNewTableDialogOpen] = useState(false);
    const [newTableName, setNewTableName] = useState("");
    const [loading, setLoading] = useState(false);

    const [reExtracting, setReExtracting] = useState(false);
    const [reExtractProgress, setReExtractProgress] = useState<{ processed: number, total: number } | null>(null);

    // Store data per table
    const [tableData, setTableData] = useState<Record<string, DataRow[]>>({});

    const [model, setModel] = useState(MODEL_OPTIONS[0].value);
    const [status, setStatus] = useState<StatusState>(null);
    const [elapsed, setElapsed] = useState<number>(0);
    const [finalTime, setFinalTime] = useState<number | null>(null);
    const timerIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const submitTimeRef = useRef<number | null>(null);

    const activeTable = tables.find(t => t.table_id === currentTable);
    const extractedData = tableData[currentTable] || [];

    // Fetch tables on mount
    useEffect(() => {
        fetchTables();
    }, []);

    // Fetch results when table changes
    useEffect(() => {
        if (currentTable) {
            fetchResults(currentTable);
        }
    }, [currentTable]);

    const fetchTables = async () => {
        try {
            const data = await documentService.getTables();
            setTables(data);

            if (data.length > 0 && !currentTable) {
                setCurrentTable(data[0].table_id);
            }
        } catch (error) {
            console.error("Error fetching tables:", error);
            toast.error("Failed to load tables");
        }
    };

    const fetchResults = async (tableId: string) => {
        try {
            const data = await documentService.getResults({ table_id: tableId, limit: 100 });

            const formattedData: DataRow[] = data.map((result: DocumentResult) => ({
                id: result.id,
                file: result.filename,
                extractText: result.extracted_text || "Extracted content...",
                ...result.fields_mapped
            }));

            setTableData(prev => ({
                ...prev,
                [tableId]: formattedData
            }));
        } catch (error) {
            console.error("Error fetching results:", error);
            toast.error("Failed to load extraction results");
        }
    };

    const startTimer = () => {
        setElapsed(0);
        if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = setInterval(() => setElapsed(prev => prev + 1), 1000);
    };

    const stopTimer = () => {
        if (timerIntervalRef.current) {
            clearInterval(timerIntervalRef.current);
            timerIntervalRef.current = null;
        }
    };

    useEffect(() => {
        return () => {
            stopTimer();
        };
    }, []);

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0] || null;

        if (file && activeTable && !activeTable.is_configured) {
            toast.error("Configuration Required", {
                description: "Please configure fields for this table before uploading files."
            });
            e.target.value = "";
            return;
        }

        setUploadedFile(file);
        setStatus(null);
        setFinalTime(null);
        setElapsed(0);
    };

    const handleRowClick = (row: DataRow) => {
        setSelectedRow(row);
        setExtractionFields(activeTable?.fields || []);
        setIsDrawerOpen(true);
    };

    const handleAddField = () => {
        const newField: ExtractionField = {
            id: Date.now(),
            field_id: `field_${Date.now()}`,
            name: "New Field",
            field_type: "text",
            is_required: false,
            display_order: extractionFields.length
        };
        setExtractionFields((prev) => [...prev, newField]);
    };

    const handleRemoveField = (fieldId: string) => {
        setExtractionFields((prev) => prev.filter(f => f.field_id !== fieldId));
    };

    const handleFieldChange = (fieldId: string, key: keyof ExtractionField, value: string) => {
        setExtractionFields(prev => prev.map(f => (f.field_id === fieldId ? { ...f, [key]: value } : f)));
    };

    const handleReExtractAll = async () => {
        if (!activeTable) return;

        setReExtracting(true);
        setReExtractProgress({ processed: 0, total: extractedData.length });

        try {
            // Re-extract each document individually
            let processed = 0;
            for (const row of extractedData) {
                try {
                    await documentService.reExtract(row.id, {
                        fields: activeTable.fields.map(f => ({
                            field_id: f.field_id,
                            name: f.name,
                            field_type: f.field_type
                        }))
                    });
                    processed++;
                    setReExtractProgress({ processed, total: extractedData.length });
                } catch (err) {
                    console.error(`Failed to re-extract document ${row.id}:`, err);
                }
            }

            toast.success("Re-extraction Complete", {
                description: `${processed} documents processed successfully`
            });

            // Refresh results
            await fetchResults(currentTable);

        } catch (error) {
            console.error("Error re-extracting:", error);
            toast.error("Re-extraction failed");
        } finally {
            setReExtracting(false);
            setReExtractProgress(null);
        }
    };

    const handleSubmitExtraction = async () => {
        if (!activeTable?.is_configured) {
            toast.error("Configuration Required");
            return;
        }

        if (!uploadedFile) {
            toast.error("Please select a file to submit.");
            return;
        }

        setStatus({ type: "polling", message: "Uploading and extracting..." });
        setFinalTime(null);
        setElapsed(0);
        submitTimeRef.current = Date.now();
        startTimer();
        setLoading(true);

        try {
            const result = await documentService.extractDocument(
                uploadedFile,
                {
                    id: currentTable,
                    name: activeTable.name,
                    fields: activeTable.fields
                },
                model
            );

            stopTimer();
            const timeTaken = Math.round((Date.now() - (submitTimeRef.current || Date.now())) / 1000);
            setFinalTime(timeTaken);
            setStatus({ type: "success", message: `Success! Completed in ${timeTaken} seconds.` });

            // Refresh results
            await fetchResults(currentTable);

            toast.success("Extraction Complete", { description: `Completed in ${timeTaken}s.` });
            setUploadedFile(null);

            // Reset file input
            const fileInput = document.getElementById('file-upload') as HTMLInputElement;
            if (fileInput) fileInput.value = '';

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Extraction failed";
            setStatus({ type: "error", message: errorMessage });
            stopTimer();
            toast.error("Extraction failed", { description: errorMessage });
        } finally {
            setLoading(false);
        }
    };

    const handleSaveConfiguration = async () => {
        if (extractionFields.length === 0) {
            toast.error("No fields configured", {
                description: "Please add at least one field before saving."
            });
            return;
        }

        try {
            await documentService.createTable({
                table_id: currentTable,
                name: activeTable?.name || "",
                description: activeTable?.description,
                fields: extractionFields.map((f, index) => ({
                    field_id: f.field_id,
                    name: f.name,
                    field_type: f.field_type,
                    is_required: f.is_required
                }))
            });

            toast.success("Configuration Saved", {
                description: "Field configuration updated successfully.",
            });

            // Refresh tables
            await fetchTables();
            setIsConfigDrawerOpen(false);

            // Ask user if they want to re-extract existing documents
            if (extractedData.length > 0) {
                toast.info("Re-extract Documents?", {
                    description: `You have ${extractedData.length} existing documents. Would you like to re-extract them with the new fields?`,
                    action: {
                        label: "Re-extract All",
                        onClick: handleReExtractAll
                    },
                    duration: 10000
                });
            }

        } catch (error) {
            console.error("Error saving configuration:", error);
            toast.error("Failed to save configuration");
        }
    };

    const handleAddTable = () => {
        setNewTableName("");
        setIsNewTableDialogOpen(true);
    };

    const handleCreateTable = async () => {
        if (!newTableName.trim()) {
            toast.error("Please enter a table name.");
            return;
        }

        try {
            const tableId = `table_${Date.now()}`;

            await documentService.createTable({
                table_id: tableId,
                name: newTableName.trim(),
                fields: []
            });

            setIsNewTableDialogOpen(false);
            setNewTableName("");

            // Refresh tables
            await fetchTables();
            setCurrentTable(tableId);

            // Open configuration drawer for new table
            setExtractionFields([]);
            setIsConfigDrawerOpen(true);

            toast.success("Table Created", {
                description: `"${newTableName}" created. Please configure fields before uploading files.`
            });
        } catch (error) {
            console.error("Error creating table:", error);
            toast.error("Failed to create table");
        }
    };

    const handleConfigureTable = () => {
        setExtractionFields(activeTable?.fields || []);
        setIsConfigDrawerOpen(true);
    };

    const handleDeleteResult = async (resultId: number) => {
        try {
            await documentService.deleteResult(resultId);
            toast.success("Result deleted");
            await fetchResults(currentTable);
        } catch (error) {
            toast.error("Failed to delete result");
        }
    };

    const statusClasses =
        status?.type === "error"
            ? "bg-destructive text-destructive-foreground"
            : status?.type === "polling"
                ? "bg-amber-400 text-black"
                : status?.type === "success"
                    ? "bg-emerald-500 text-white"
                    : "bg-muted text-muted-foreground";

    return (
        <>
            <div className="flex h-[calc(100vh-8rem)] gap-4">
                {activeTable ? (
                    <div className="flex-1 flex flex-col gap-4">

                        {/* Upload & Table Selection */}
                        <Card className="p-6 bg-card border-border">
                            <div className="flex items-center gap-4">
                                <div className="flex-1">
                                    <Label htmlFor="file-upload" className="text-sm font-medium text-foreground mb-2 block">
                                        Upload Data
                                    </Label>
                                    <div className="flex gap-2">
                                        <Input
                                            id="file-upload"
                                            type="file"
                                            accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.webp"
                                            onChange={handleFileUpload}
                                            className="flex-1"
                                            disabled={!activeTable?.is_configured || loading}
                                        />
                                        <Button
                                            onClick={handleSubmitExtraction}
                                            disabled={!activeTable?.is_configured || !uploadedFile || loading}
                                            className="bg-primary text-primary-foreground hover:bg-primary/90">
                                            <Upload className="w-4 h-4 mr-2" />
                                            {loading ? "Processing..." : "Extract"}
                                        </Button>
                                    </div>
                                    {uploadedFile && (
                                        <p className="text-sm text-muted-foreground mt-2">
                                            Selected: {uploadedFile.name}
                                        </p>
                                    )}
                                    {activeTable && !activeTable.is_configured && (
                                        <p className="text-sm text-amber-600 mt-2 flex items-center gap-1">
                                            <Settings className="w-4 h-4" />
                                            Configure fields before uploading files
                                        </p>
                                    )}
                                </div>
                                <div className="w-64">
                                    <Label className="text-sm font-medium text-foreground mb-2 block">
                                        Table Type
                                    </Label>

                                    <div className="flex gap-2">
                                        <Select value={currentTable} onValueChange={setCurrentTable}>
                                            <SelectTrigger className="w-full">
                                                <SelectValue placeholder="Select table" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {tables.map(table => (
                                                    <SelectItem key={table.table_id} value={table.table_id}>
                                                        {table.name} {!table.is_configured && "⚠️"}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>

                                        <Button
                                            onClick={handleAddTable}
                                            variant="outline"
                                            size="icon"
                                            className="shrink-0"
                                        >
                                            <Plus className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            </div>
                            {status && (
                                <div className={`mt-4 rounded-md px-4 py-2 text-sm font-medium shadow-sm ${statusClasses}`}>
                                    <div className="flex items-center justify-between">
                                        <span>{status.message}</span>
                                        <div className="text-xs font-normal">
                                            {status.type === "polling" && <span>Elapsed: {elapsed}s</span>}
                                            {status.type === "success" && finalTime !== null && <span>Total time: {finalTime}s</span>}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </Card>

                        <Card className="flex-1 overflow-hidden bg-card border-border">
                            <div className="h-full overflow-auto">
                                <Table>
                                    <TableHeader className="sticky top-0 bg-muted/50 backdrop-blur">
                                        <TableRow className="border-border hover:bg-transparent">
                                            <TableHead className="w-12 text-muted-foreground">#</TableHead>
                                            <TableHead className="text-muted-foreground">
                                                <div className="flex items-center gap-2">
                                                    <FileText className="w-4 h-4" />
                                                    File
                                                </div>
                                            </TableHead>
                                            <TableHead className="text-muted-foreground">Extract text</TableHead>
                                            {activeTable?.fields.map(field => (
                                                <TableHead key={field.field_id} className="text-muted-foreground">
                                                    {field.name}
                                                </TableHead>
                                            ))}
                                            <TableHead className="w-20"></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {extractedData.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={4 + (activeTable?.fields.length || 0)} className="text-center text-muted-foreground py-8">
                                                    {activeTable?.is_configured
                                                        ? "No data yet. Upload and extract files to see results here."
                                                        : "Configure fields for this table to start extracting data."}
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            extractedData.map((row) => (
                                                <TableRow
                                                    key={row.id}
                                                    className={`cursor-pointer border-border ${selectedRow?.id === row.id ? "bg-accent/50" : "hover:bg-accent/30"
                                                        }`}
                                                >
                                                    <TableCell
                                                        className="text-muted-foreground"
                                                        onClick={() => handleRowClick(row)}
                                                    >
                                                        {row.id}
                                                    </TableCell>
                                                    <TableCell
                                                        className="font-mono text-sm text-foreground"
                                                        onClick={() => handleRowClick(row)}
                                                    >
                                                        {row.file}
                                                    </TableCell>
                                                    <TableCell
                                                        className="text-muted-foreground max-w-md truncate"
                                                        onClick={() => handleRowClick(row)}
                                                    >
                                                        {row.extractText}
                                                    </TableCell>
                                                    {activeTable?.fields.map(field => (
                                                        <TableCell
                                                            key={field.field_id}
                                                            className="text-foreground"
                                                            onClick={() => handleRowClick(row)}
                                                        >
                                                            {row[field.field_id] || "-"}
                                                        </TableCell>
                                                    ))}
                                                    <TableCell>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleDeleteResult(row.id);
                                                            }}
                                                        >
                                                            <Trash2 className="w-4 h-4 text-destructive" />
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        )}
                                    </TableBody>
                                </Table>
                            </div>
                        </Card>
                    </div>
                ) : (
                    <div className="flex-1 flex items-center justify-center">
                        <div className="text-center">
                            <h2 className="text-2xl font-semibold text-foreground mb-4">No Tables Available</h2>
                            <p className="text-muted-foreground mb-6">Please create a new table to start extracting data.</p>
                            <Button onClick={handleAddTable} className="bg-primary text-primary-foreground hover:bg-primary/90">
                                <Plus className="w-4 h-4 mr-2" />
                                Create New Table
                            </Button>
                        </div>
                    </div>
                )}

                {/* Rest of the component remains the same - Quick Actions sidebar, drawers, etc. */}
                {activeTable && (
                    <div className="w-80 flex flex-col gap-4">
                        <Card className="p-4 bg-card border-border">
                            <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
                                <TableIcon className="w-4 h-4" />
                                Quick Actions
                            </h3>
                            <div className="space-y-2">
                                <Button
                                    onClick={handleConfigureTable}
                                    variant="outline"
                                    className="w-full"
                                >
                                    <Settings className="w-4 h-4 mr-2" />
                                    Configure Table
                                </Button>
                                <Button
                                    onClick={() => setIsDrawerOpen(true)}
                                    variant="outline"
                                    className="w-full"
                                    disabled={!activeTable?.is_configured}
                                >
                                    <Eye className="w-4 h-4 mr-2" />
                                    View Configuration
                                </Button>
                                <Button
                                    onClick={handleReExtractAll}
                                    variant="outline"
                                    className="w-full"
                                    disabled={!activeTable?.is_configured || extractedData.length === 0 || reExtracting}
                                >
                                    <Upload className="w-4 h-4 mr-2" />
                                    {reExtracting ? `Re-extracting (${reExtractProgress?.processed}/${reExtractProgress?.total})` : "Re-extract All"}
                                </Button>
                            </div>
                        </Card>

                        <Card className="p-4 bg-card border-border">
                            <h3 className="font-semibold text-foreground mb-2">Active Fields</h3>
                            {activeTable?.is_configured ? (
                                <div className="space-y-2">
                                    {(activeTable?.fields || []).map(field => (
                                        <div key={field.field_id} className="p-2 bg-muted/50 rounded-md text-sm">
                                            <div className="font-medium text-foreground">{field.name}</div>
                                            <div className="text-xs text-muted-foreground">{field.field_type}</div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-sm text-muted-foreground p-4 text-center border border-dashed rounded-md">
                                    No fields configured. Click "Configure Table" to add fields.
                                </div>
                            )}
                        </Card>
                    </div>
                )}
            </div>

            {/* Configuration Drawer */}
            <Drawer open={isConfigDrawerOpen} onOpenChange={setIsConfigDrawerOpen} direction="right">
                <DrawerContent className="fixed h-screen right-0 left-auto w-[600px] rounded-none border-none rounded-l-lg bg-card shadow-xl">
                    <DrawerHeader className="border-b">
                        <DrawerTitle>Configure Table: {activeTable?.name}</DrawerTitle>
                        <DrawerDescription>
                            Add and configure fields for data extraction. At least one field is required.
                        </DrawerDescription>
                    </DrawerHeader>

                    <div className="p-6 overflow-y-auto flex-1 space-y-4">
                        <div className="flex items-center justify-between">
                            <h4 className="font-medium text-foreground">Extraction Fields</h4>
                            <Button onClick={handleAddField} size="sm" variant="outline">
                                <Plus className="w-4 h-4 mr-1" />
                                Add Field
                            </Button>
                        </div>

                        {extractionFields.length === 0 && (
                            <div className="text-center p-8 border border-dashed rounded-lg">
                                <p className="text-muted-foreground mb-4">No fields configured yet</p>
                                <Button onClick={handleAddField} variant="outline">
                                    <Plus className="w-4 h-4 mr-2" />
                                    Add Your First Field
                                </Button>
                            </div>
                        )}

                        {extractionFields.map((field, index) => (
                            <Card key={field.field_id} className="p-4 bg-card">
                                <div className="flex items-start justify-between mb-3">
                                    <div className="text-sm font-medium text-foreground">Field {index + 1}</div>
                                    <Button onClick={() => handleRemoveField(field.field_id)} size="sm" variant="ghost">
                                        <Trash2 className="w-4 h-4 text-destructive" />
                                    </Button>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <div>
                                        <Label className="text-xs text-muted-foreground">Field Name</Label>
                                        <Input
                                            value={field.name}
                                            onChange={(e) => handleFieldChange(field.field_id, "name", e.target.value)}
                                            className="mt-1"
                                            placeholder="e.g., Invoice Number, Total Amount"
                                        />
                                    </div>

                                    <div>
                                        <Label className="text-xs text-muted-foreground">Type</Label>
                                        <ShadSelect
                                            value={field.field_type}
                                            onValueChange={(value) => handleFieldChange(field.field_id, "field_type", value)}
                                        >
                                            <SelectTrigger className="mt-1">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="text">Text</SelectItem>
                                                <SelectItem value="number">Number</SelectItem>
                                                <SelectItem value="date">Date</SelectItem>
                                                <SelectItem value="currency">Currency</SelectItem>
                                                <SelectItem value="email">Email</SelectItem>
                                            </SelectContent>
                                        </ShadSelect>
                                    </div>
                                </div>
                            </Card>
                        ))}
                    </div>

                    <DrawerFooter className="flex-row gap-2 border-t">
                        <DrawerClose asChild>
                            <Button variant="outline" className="flex-1">Cancel</Button>
                        </DrawerClose>
                        <Button
                            onClick={handleSaveConfiguration}
                            className="flex-1"
                            disabled={extractionFields.length === 0}
                        >
                            Save Configuration
                        </Button>
                    </DrawerFooter>
                </DrawerContent>
            </Drawer>

            {/* View Configuration Drawer - Same as before */}
            <Drawer open={isDrawerOpen} onOpenChange={setIsDrawerOpen} direction="right">
                <DrawerContent className="fixed h-screen right-0 left-auto w-[600px] rounded-none border-none rounded-l-lg bg-card shadow-xl">
                    <DrawerHeader className="border-b">
                        <DrawerTitle>Field Configuration</DrawerTitle>
                        <DrawerDescription>
                            {selectedRow ? `Viewing extraction for ${selectedRow.file}` : "View extraction fields"}
                        </DrawerDescription>
                    </DrawerHeader>

                    <div className="p-6 overflow-y-auto flex-1 space-y-4">
                        {selectedRow && (
                            <Card className="p-4 bg-muted/20">
                                <h4 className="font-medium text-sm mb-2 text-foreground">Source Data Preview</h4>
                                <div className="text-xs text-muted-foreground space-y-1">
                                    <div><span className="font-medium">File:</span> {selectedRow.file}</div>
                                    <div><span className="font-medium">Extract Text:</span> {selectedRow.extractText}</div>
                                </div>
                            </Card>
                        )}

                        <div className="space-y-3">
                            <h4 className="font-medium text-foreground">Extracted Fields</h4>
                            {activeTable?.fields.map(field => (
                                <Card key={field.field_id} className="p-4 bg-card">
                                    <div className="grid grid-cols-1 gap-3">
                                        <div>
                                            <Label className="text-xs text-muted-foreground">Field Name</Label>
                                            <div className="mt-1 text-sm font-medium text-foreground">{field.name}</div>
                                        </div>

                                        <div>
                                            <Label className="text-xs text-muted-foreground">Type</Label>
                                            <div className="mt-1 text-sm text-foreground capitalize">{field.field_type}</div>
                                        </div>

                                        {selectedRow && (
                                            <div className="p-3 bg-muted/30 rounded text-sm">
                                                <div className="font-medium text-foreground mb-1">Extracted Value:</div>
                                                <div className="text-foreground">
                                                    {selectedRow[field.field_id] || "-"}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </div>

                    <DrawerFooter className="flex-row gap-2 border-t">
                        <DrawerClose asChild>
                            <Button variant="outline" className="flex-1">Close</Button>
                        </DrawerClose>
                    </DrawerFooter>
                </DrawerContent>
            </Drawer>

            {/* New Table Dialog */}
            <Dialog open={isNewTableDialogOpen} onOpenChange={setIsNewTableDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Create New Table</DialogTitle>
                        <DialogDescription>
                            Enter a name for your new extraction table. You'll configure fields after creation.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="py-4">
                        <Label htmlFor="table-name" className="text-sm font-medium text-foreground">
                            Table Name
                        </Label>
                        <Input
                            id="table-name"
                            value={newTableName}
                            onChange={(e) => setNewTableName(e.target.value)}
                            placeholder="e.g., Invoices, Receipts, Contracts"
                            className="mt-2"
                            onKeyDown={(e) => {
                                if (e.key === "Enter") handleCreateTable();
                            }}
                        />
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsNewTableDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleCreateTable}>Create Table</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}