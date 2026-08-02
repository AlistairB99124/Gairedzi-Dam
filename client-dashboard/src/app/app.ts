import { CommonModule, JsonPipe } from '@angular/common';
import { Component, computed, signal } from '@angular/core';

type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
type DashboardTab = 'summary' | 'artifacts' | 'json';

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

interface StressSummary {
  source_vtu: string;
  element_count: number;
  max_tensile_principal_stress_pa: {
    element_id: number;
    value_pa: number;
    centroid_xyz_m: [number, number, number];
  };
  max_compressive_principal_stress_pa: {
    element_id: number;
    value_pa: number;
    centroid_xyz_m: [number, number, number];
  };
  note?: string;
  tensile_strength_pa?: number;
  tension_utilization?: number;
  client_expected_tension_mpa?: number;
  client_expected_compression_mpa?: number;
  detailing_assessment?: {
    critical_zone?: string;
    notes?: string[];
  };
}

interface SweepCase {
  case_name: string;
  downstream_head_m: number;
  max_tension_mpa: number;
  max_compression_mpa: number;
}

interface ResultArtifact {
  title: string;
  path: string;
  kind: 'image' | 'file';
}

@Component({
  selector: 'app-root',
  imports: [CommonModule, JsonPipe],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly activeTab = signal<DashboardTab>('summary');

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
  protected readonly isLoadingJson = signal<boolean>(false);
  protected readonly jsonError = signal<string | null>(null);

  protected readonly artifacts = signal<ResultArtifact[]>([
    { title: 'Client Stress Report', path: '/results/client_stress_report.png', kind: 'image' },
    { title: 'Principal Stress Distribution', path: '/results/principal_stress_distribution.png', kind: 'image' },
    { title: 'Critical Stress Locations', path: '/results/critical_stress_locations.png', kind: 'image' },
    { title: 'Orientation Sketch', path: '/results/arch_dam_orientations.png', kind: 'image' },
    { title: 'Stress Summary JSON', path: '/results/stress_summary.json', kind: 'file' },
    { title: 'Principal Stress by Element CSV', path: '/results/principal_stress_by_element.csv', kind: 'file' },
    { title: 'Load Case Comparison JSON', path: '/results/load_case_comparison.json', kind: 'file' },
    { title: 'Load Case Comparison CSV', path: '/results/load_case_comparison.csv', kind: 'file' },
    { title: 'VTU Output (ParaView)', path: '/results/dam_results_t0001.vtu', kind: 'file' }
  ]);

  protected readonly stressSummary = signal<StressSummary | null>(null);
  protected readonly sweepCases = signal<SweepCase[]>([]);
  protected readonly isLoadingResults = signal<boolean>(false);
  protected readonly resultsError = signal<string | null>(null);
  protected readonly lastLoadedAt = signal<Date | null>(null);

  protected readonly selectedFileTitle = computed(() => {
    const selected = this.files().find((file) => file.filename === this.selectedFilename());
    return selected ? selected.title : this.selectedFilename();
  });

  protected readonly jsonSummary = computed<FileSummary | null>(() => {
    const value = this.data();
    return value === null ? null : this.summarize(value);
  });

  protected readonly maxTensionMpa = computed(() => {
    const summary = this.stressSummary();
    return summary ? summary.max_tensile_principal_stress_pa.value_pa / 1_000_000 : null;
  });

  protected readonly maxCompressionMpa = computed(() => {
    const summary = this.stressSummary();
    return summary ? summary.max_compressive_principal_stress_pa.value_pa / 1_000_000 : null;
  });

  protected readonly tensionExpectedGapMpa = computed(() => {
    const summary = this.stressSummary();
    const tension = this.maxTensionMpa();
    if (!summary || tension === null || summary.client_expected_tension_mpa === undefined) {
      return null;
    }
    return tension - summary.client_expected_tension_mpa;
  });

  constructor() {
    this.refresh();
  }

  protected setTab(tab: DashboardTab): void {
    this.activeTab.set(tab);
  }

  protected async onSelectFile(filename: string): Promise<void> {
    if (filename === this.selectedFilename()) {
      return;
    }

    this.selectedFilename.set(filename);
    await this.loadSelectedJsonFile();
  }

  protected async refresh(): Promise<void> {
    await Promise.all([this.loadResults(), this.loadSelectedJsonFile()]);
  }

  private async loadResults(): Promise<void> {
    this.isLoadingResults.set(true);
    this.resultsError.set(null);

    try {
      const [summaryResponse, sweepResponse] = await Promise.all([
        fetch('/results/stress_summary.json'),
        fetch('/results/load_case_comparison.json')
      ]);

      if (!summaryResponse.ok) {
        throw new Error(`HTTP ${summaryResponse.status} while loading stress summary.`);
      }

      if (!sweepResponse.ok) {
        throw new Error(`HTTP ${sweepResponse.status} while loading load case comparison.`);
      }

      this.stressSummary.set((await summaryResponse.json()) as StressSummary);
      this.sweepCases.set((await sweepResponse.json()) as SweepCase[]);
      this.lastLoadedAt.set(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error while loading result files.';
      this.resultsError.set(message);
      this.stressSummary.set(null);
      this.sweepCases.set([]);
    } finally {
      this.isLoadingResults.set(false);
    }
  }

  private async loadSelectedJsonFile(): Promise<void> {
    this.isLoadingJson.set(true);
    this.jsonError.set(null);

    try {
      const response = await fetch(`/data/${this.selectedFilename()}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status} while loading ${this.selectedFilename()}`);
      }

      const json = (await response.json()) as JsonValue;
      this.data.set(json);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error while loading JSON file.';
      this.jsonError.set(message);
      this.data.set(null);
    } finally {
      this.isLoadingJson.set(false);
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
