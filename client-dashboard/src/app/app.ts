import { CommonModule, JsonPipe } from '@angular/common';
import { Component, computed, signal } from '@angular/core';

type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

interface DataFile {
  filename: string;
  title: string;
}

interface FileSummary {
  rootType: 'object' | 'array' | 'value';
  objectKeys: number;
  arrayNodes: number;
  primitiveValues: number;
  maxDepth: number;
}

@Component({
  selector: 'app-root',
  imports: [CommonModule, JsonPipe],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly files = signal<DataFile[]>([
    { filename: 'Computational_Grid_Controls.json', title: 'Computational Grid Controls' },
    { filename: 'Concrete_Material_Properties.json', title: 'Concrete Material Properties' },
    { filename: 'Dam_Base_Contours_clean.json', title: 'Dam Base Contours (Clean)' },
    { filename: 'Dam_Base_Contours.json', title: 'Dam Base Contours (Raw)' },
    { filename: 'Env_Boundaries_And_Loads.json', title: 'Environment Boundaries and Loads' },
    { filename: 'other_data.json', title: 'Other Data' }
  ]);

  protected readonly selectedFilename = signal<string>(this.files()[0].filename);
  protected readonly data = signal<JsonValue | null>(null);
  protected readonly isLoading = signal<boolean>(false);
  protected readonly error = signal<string | null>(null);
  protected readonly lastLoadedAt = signal<Date | null>(null);

  protected readonly selectedFileTitle = computed(() => {
    const selected = this.files().find((file) => file.filename === this.selectedFilename());
    return selected ? selected.title : this.selectedFilename();
  });

  protected readonly summary = computed<FileSummary | null>(() => {
    const value = this.data();
    return value === null ? null : this.summarize(value);
  });

  constructor() {
    this.loadSelectedFile();
  }

  protected async onSelectFile(filename: string): Promise<void> {
    if (filename === this.selectedFilename()) {
      return;
    }

    this.selectedFilename.set(filename);
    await this.loadSelectedFile();
  }

  protected async refresh(): Promise<void> {
    await this.loadSelectedFile();
  }

  private async loadSelectedFile(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);

    try {
      const response = await fetch(`/data/${this.selectedFilename()}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status} while loading ${this.selectedFilename()}`);
      }

      const json = (await response.json()) as JsonValue;
      this.data.set(json);
      this.lastLoadedAt.set(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error while loading JSON file.';
      this.error.set(message);
      this.data.set(null);
    } finally {
      this.isLoading.set(false);
    }
  }

  private summarize(value: JsonValue): FileSummary {
    let objectKeys = 0;
    let arrayNodes = 0;
    let primitiveValues = 0;
    let maxDepth = 0;

    const visit = (node: JsonValue, depth: number): void => {
      if (depth > maxDepth) {
        maxDepth = depth;
      }

      if (Array.isArray(node)) {
        arrayNodes += 1;
        for (const child of node) {
          visit(child, depth + 1);
        }
        return;
      }

      if (node !== null && typeof node === 'object') {
        const entries = Object.entries(node);
        objectKeys += entries.length;
        for (const [, child] of entries) {
          visit(child, depth + 1);
        }
        return;
      }

      primitiveValues += 1;
    };

    visit(value, 1);

    let rootType: FileSummary['rootType'] = 'value';
    if (Array.isArray(value)) {
      rootType = 'array';
    } else if (value !== null && typeof value === 'object') {
      rootType = 'object';
    }

    return {
      rootType,
      objectKeys,
      arrayNodes,
      primitiveValues,
      maxDepth
    };
  }
}
